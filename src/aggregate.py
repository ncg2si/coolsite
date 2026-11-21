import time
from pathlib import Path
from pyspark.sql import functions as F
import pandas as pd

from spark_utils import get_spark
from classify import classify
from utils.log import get_logger
from paths import SILVER, GOLD, SCENARIOS_FILE
from contract import MIN_COVERAGE_CITY_YEAR
 
def load_scenarios() -> list:
    return pd.read_csv(SCENARIOS_FILE).to_dict(orient='records')


def count_modes(silver,scenario):
    classified = classify(silver,scenario["design"] ,scenario)
    classified = classified.withColumn("scenario",F.lit(scenario["scenario"]))
    return (classified.groupBy("city","year","scenario","mode")
                .agg(F.count("*").alias("hours"),
                     F.sum("water_degree").alias("water_degree_hours"),
                     F.sum("chiller_degree").alias("chiller_degree_hours"),
                     F.sum(F.col("humidity_limited").cast('int')).alias("humidity_limited_hours")
                     ))


def add_mode_share (counts):
    totals = counts.groupBy("city","year","scenario").agg(F.sum("hours").alias("total_hours"))
    joined = counts.join(totals, on = ["city","year","scenario"])
    return joined.withColumn("mode_share", F.col("hours")/F.col("total_hours"))


def add_coverage(df):
    """Add expected_hours, coverage, incomplete per row 
    needs columns year, total_hours
    """
    expected_hours = F.datediff(F.make_date(F.col("year")+1, F.lit(1),F.lit(1)), F.make_date(F.col("year"), F.lit(1),F.lit(1)))*24
    return(df.withColumn("expected_hours",expected_hours)
            .withColumn("coverage",F.col("total_hours")/F.col("expected_hours"))
            .withColumn("incomplete", F.col("coverage") < MIN_COVERAGE_CITY_YEAR)           
           )


log = get_logger(Path(__file__).stem)


def build_gold():
    t0 = time.perf_counter()
    log.info("gold run started")
    silver = None
    try:
        spark = get_spark()
        silver = spark.read.parquet(str(SILVER)).cache()
        scenarios = load_scenarios()
        all_modes = None
        for scenario in scenarios:
            c_mode = count_modes(silver,scenario)
            if all_modes is None:
                all_modes = c_mode
            else: 
                all_modes = all_modes.unionByName(c_mode)
        gold = (add_coverage(add_mode_share(all_modes)
                .withColumn("processed_at", F.current_timestamp())))
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
    build_gold()
    
    