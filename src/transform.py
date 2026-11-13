from pyspark.sql import DataFrame, functions as F

from contract import CONTRACT_VERSION, WEATHER_MODEL
from utils.wetbulb import wet_bulb_stull
from validate import validate

SILVER = "data/silver" 
QUARANTINE = "data/quarantine"

SILVER_COLUMNS = ["city", "year", "time", "temperature_c", "humidity_pct", "dew_point_c",
                  "wet_bulb_c", "source_model", "contract_version", "processed_at"]

def to_silver(valid: DataFrame) -> DataFrame:
    """Pure: add derived and lineage columns and fix the silver schema."""
    return (valid
            .withColumn("wet_bulb_c", wet_bulb_stull(F.col("temperature_c"),F.col("humidity_pct")))
            .withColumn("year", F.year(F.col("time")))
            .withColumn("source_model", F.lit(WEATHER_MODEL))
            .withColumn("contract_version",F.lit(CONTRACT_VERSION))
            .withColumn("processed_at",F.current_timestamp())
            .select(*SILVER_COLUMNS)

    )

def write_partitioned(df: DataFrame, path: str) -> None:
    """ IO: remove city/year partition present in df"""
    (df.repartition("city","year") #avoid having 200 files
        .write
        .mode("overwrite")
        .option("partitionOverwriteMode", "dynamic") #static would delete the whole silver data
        .partitionBy("city","year")
        .parquet(path)
)

def run(city: str, start: str, end: str) -> None:
    valid, quarantine = validate(city, start, end)
    write_partitioned(to_silver(valid),SILVER)
    write_partitioned(quarantine.withColumn("year",F.year(F.col("time"))),QUARANTINE)

if __name__ == "__main__":
    run("frankfurt","2025-01-01", "2025-12-31")
    #run("barcelona","2025-01-01", "2025-12-31")

