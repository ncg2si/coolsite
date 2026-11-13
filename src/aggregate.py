
import json
import time
from pathlib import Path
from pyspark.sql import functions as F

from spark_utils import get_spark
from classify import classify, DEFAULT_PARAMS
from utils.log import get_logger
from paths import SILVER, GOLD
 

def count_modes(silver,design):
    classified = classify(silver, design)
    return classified.groupBy("city","year","design","mode").agg(F.count("*").alias("hours"))


def add_mode_share (counts):
    totals = counts.groupBy("city","year","design").agg(F.sum("hours").alias("total_hours"))
    joined = counts.join(totals, on = ["city","year","design"])
    return joined.withColumn("mode_share", F.col("hours")/F.col("total_hours"))





log = get_logger(Path(__file__).stem)


def run():
    t0 = time.perf_counter()
    log.info("gold run started")
    silver = None
    try:
        spark = get_spark()
        silver = spark.read.parquet(str(SILVER)).cache()
        all_modes = count_modes(silver,"direct").unionByName(count_modes(silver,"indirect"))
        gold = (add_mode_share(all_modes)
                .withColumn("params",F.lit(json.dumps(DEFAULT_PARAMS)))
                .withColumn("processed_at", F.current_timestamp()))
        gold.coalesce(1).write.mode("overwrite").parquet(str(GOLD))
        log.info(f"gold written: {gold.count()} rows")
        log.info(f"gold run finished: SUCCESS ({time.perf_counter()- t0:.1f} s)")
    except Exception:
        log.exception("gold run FAILED")
        raise
    finally:
        if silver is not None:
            silver.unpersist()
            
if __name__ == "__main__":
    run()
    
    