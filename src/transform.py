import time
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from contract import CONTRACT_VERSION, WEATHER_MODEL
from spark_utils import get_spark
from utils.log import get_logger
from paths import SILVER, QUARANTINE
from utils.wetbulb import wet_bulb_stull
from validate import validate

log = get_logger(Path(__file__).stem)

def make_run_id(city:str, start:str) -> str:
    """build a run_id UTC timestamp + city + year to a run """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{city}_{start[:4]}"


SILVER_COLUMNS = ["city", "year", "time", "temperature_c", "humidity_pct", "dew_point_c",
                  "wet_bulb_c", "source_model", "contract_version", "processed_at","run_id"]

def to_silver(valid: DataFrame, run_id: str) -> DataFrame:
    """Pure: add derived and lineage columns and fix the silver schema."""
    return (valid
            .withColumn("wet_bulb_c", wet_bulb_stull(F.col("temperature_c"),F.col("humidity_pct")))
            .withColumn("year", F.year(F.col("time")))
            .withColumn("source_model", F.lit(WEATHER_MODEL))
            .withColumn("contract_version",F.lit(CONTRACT_VERSION))
            .withColumn("processed_at",F.current_timestamp())
            .withColumn("run_id",F.lit(run_id))
            .select(*SILVER_COLUMNS)

    )

def write_partitioned(df: DataFrame, path: str) -> None:
    """ IO: replace city/year partition present in df"""
    (df.repartition("city","year") #avoid having 200 files
        .write
        .mode("overwrite")
        .option("partitionOverwriteMode", "dynamic") #static would delete the whole silver data
        .partitionBy("city","year")
        .parquet(path)
)

def transform_city_year(city: str, start: str, end: str) -> None:
    run_id = make_run_id(city,start)
    t0 = time.perf_counter()
    log.info(f"[{run_id}] run started: {city} {start} -> {end}")
    try:
        valid, quarantine = validate(city, start, end)
        n_valid, n_quarantine = valid.count(), quarantine.count()
        log.info(f"[{run_id}] validate done: valid = {n_valid} quarantine = {n_quarantine}")
        write_partitioned(to_silver(valid, run_id), str(SILVER))
        log.info(f"[{run_id}] silver written: {n_valid} rows")
        write_partitioned(quarantine.withColumn("year",F.year(F.col("time"))), str(QUARANTINE))
        log.info(f"[{run_id}] quarantine written: {n_quarantine} rows")
        log.info(f"[{run_id}] run finished: SUCCESS ({time.perf_counter() - t0:.1f} s)")
    except Exception:
        log.exception(f"[{run_id}] run FAILED")
        raise
    finally:
        get_spark().catalog.clearCache()
if __name__ == "__main__":
    #run("frankfurt","2025-01-01", "2025-12-31")
    transform_city_year("berlin","1979-01-01", "1979-12-31")

