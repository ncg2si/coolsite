import time
from datetime import UTC, datetime
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from contract import CONTRACT_VERSION, WEATHER_MODEL
from paths import ON_DATABRICKS, SILVER, STAGING
from spark_utils import get_spark
from storage import merge_into, write_table
from utils.log import get_logger
from utils.wetbulb import wet_bulb_stull
from validate import validate

log = get_logger(Path(__file__).stem)


def make_run_id(city: str, start: str) -> str:
    """build a run_id UTC timestamp + city + year to a run"""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{city}_{start[:4]}"


SILVER_COLUMNS = [
    "city",
    "year",
    "time",
    "temperature_c",
    "humidity_pct",
    "dew_point_c",
    "wet_bulb_c",
    "source_model",
    "contract_version",
    "processed_at",
    "run_id",
]


def to_silver(valid: DataFrame, run_id: str) -> DataFrame:
    """Pure: add derived and lineage columns and fix the silver schema."""
    return (
        valid.withColumn(
            "wet_bulb_c", wet_bulb_stull(F.col("temperature_c"), F.col("humidity_pct"))
        )
        .withColumn("year", F.year(F.col("time")))
        .withColumn("source_model", F.lit(WEATHER_MODEL))
        .withColumn("contract_version", F.lit(CONTRACT_VERSION))
        .withColumn("processed_at", F.current_timestamp())
        .withColumn("run_id", F.lit(run_id))
        .select(*SILVER_COLUMNS)
    )


def write_partitioned(df: DataFrame, path: str) -> None:
    """IO: replace city/year partition present in df"""
    (
        df.repartition("city", "year")  # avoid having 200 files
        .write.mode("overwrite")
        .option(
            "partitionOverwriteMode", "dynamic"
        )  # static would delete the whole silver data
        .partitionBy("city", "year")
        .parquet(path)
    )


def upsert_silver(new: DataFrame, city: str, year: int) -> None:
    """New rows win on (city,time), other rows of (city,year) partition are kept
    Locally :Writes via a staging folder: Spark cannot overwrite a path it is reading in the same plan
    On Databricks: Delta MERGE
    """
    spark = get_spark()
    if ON_DATABRICKS:
        merge_into(spark, new, "silver", "weather_hourly", keys=["city", "time"])
        return
    # local: unchanged
    in_partition = (F.col("city") == city) & (F.col("year") == year)
    partition_dir = SILVER / f"city={city}" / f"year={year}"
    if partition_dir.exists():
        # existing rows of this partition (empty DataFrame if the partition does not exist)
        existing = spark.read.parquet(str(SILVER)).filter(in_partition)
        # keep old rows whose keys (city,time) are not in the new data:
        kept_old = existing.join(
            new.select("city", "time"), on=["city", "time"], how="left_anti"
        )
        # merge with all new rows
        merged = kept_old.unionByName(new)
    else:
        merged = new
    # write to staging
    staging = STAGING / "silver"
    write_partitioned(merged, str(staging))
    # copy this partition from staging to silver
    write_partitioned(
        spark.read.parquet(str(staging)).filter(in_partition), str(SILVER)
    )


def transform_city_year(city: str, start: str, end: str) -> None:
    run_id = make_run_id(city, start)
    t0 = time.perf_counter()
    log.info(f"[{run_id}] run started: {city} {start} -> {end}")
    try:
        valid, quarantine, stats = validate(city, start, end)
        # n_valid, n_quarantine = valid.count(), quarantine.count()
        n_valid, n_quarantine = stats["n_valid"], stats["n_quarantine"]
        log.info(
            f"[{run_id}] validate done: valid = {n_valid} quarantine = {n_quarantine}"
        )
        year = int(start[:4])
        upsert_silver(to_silver(valid, run_id), city, year)
        log.info(f"[{run_id}] silver written: {n_valid} rows")
        if n_quarantine > 0:
            quarantine = (
                quarantine.withColumn("year", F.year(F.col("time")))
                .withColumn("run_id", F.lit(run_id))
                .withColumn("processed_at", F.current_timestamp())
            )
            write_table(
                quarantine,
                "silver",
                "quarantine",
                mode="append",
                partition_by=["city", "year"],
            )
            log.info(f"[{run_id}] quarantine appended: {n_quarantine} rows")
        else:
            log.info(f"[{run_id}] quarantine empty -> skipped")
        log.info(f"[{run_id}] run finished: SUCCESS ({time.perf_counter() - t0:.1f} s)")
    except Exception:
        log.exception(f"[{run_id}] run FAILED")
        raise
    finally:
        get_spark().catalog.clearCache()


if __name__ == "__main__":
    # run("frankfurt","2025-01-01", "2025-12-31")
    transform_city_year("berlin", "1979-01-01", "1979-12-31")
