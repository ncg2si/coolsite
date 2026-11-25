import time
from pathlib import Path
from pyspark.sql import functions as F
import pandas as pd

from spark_utils import get_spark
from classify import classify
from utils.log import get_logger
from paths import SILVER, GOLD_FACT_COOLING_HOURS, SCENARIOS_FILE, GOLD_FACT_CITY_YEAR
from paths import GOLD_DIM_MODE, GOLD_DIM_SCENARIO, GOLD_DIM_CITY, GOLD_DIM_YEAR
from contract import MIN_COVERAGE_CITY_YEAR
from dimensions import build_dim_mode, build_dim_scenario, build_dim_city, build_dim_year
from storage import read_table, write_table, table_exists
 
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
        # gold = (add_coverage(add_mode_share(all_modes)
        #         .withColumn("processed_at", F.current_timestamp())))
        # totals = silver.groupBy("city","year").agg(F.count("*").alias("total_hours"))
        # all_modes = all_modes.join(totals,on= ["city","year"])
        # grain: 1 row = city + year + scenario + mode
        fact_cooling_hours = all_modes.withColumn("processed_at", F.current_timestamp())
        # grain: 1 row = city + year  (count hours straight from silver, no join)
        totals = silver.groupBy("city","year").agg(F.count("*").alias("total_hours"))
        fact_city_year = (add_coverage(totals)
                        .withColumn("processed_at", F.current_timestamp()))
        fact_cooling_hours_cols = ["city","year","scenario","mode","hours","water_degree_hours","chiller_degree_hours","humidity_limited_hours","processed_at"]
        fact_city_year_cols = ["city","year","expected_hours","total_hours","coverage","incomplete","processed_at"]
        #fact_cooling_hours.coalesce(1).select(fact_cooling_hours_cols).write.mode("overwrite").parquet(str(GOLD_FACT_COOLING_HOURS))
        #fact_city_year.coalesce(1).select(fact_city_year_cols).write.mode("overwrite").parquet(str(GOLD_FACT_CITY_YEAR))
        write_table(fact_cooling_hours.coalesce(1).select(fact_cooling_hours_cols),"gold","fact_cooling_hours")
        write_table(fact_city_year.coalesce(1).select(fact_city_year_cols),"gold","fact_city_year")
        dim_mode = build_dim_mode(spark)
        write_table(dim_mode,"gold","dim_mode")
        #dim_mode.write.mode("overwrite").parquet(str(GOLD_DIM_MODE))
        dim_scenario = build_dim_scenario(spark)
        write_table(dim_scenario,"gold","dim_scenario")
        #dim_scenario.write.mode("overwrite").parquet(str(GOLD_DIM_SCENARIO))
        dim_city = build_dim_city(spark)
        dim_city.write.mode("overwrite").parquet(str(GOLD_DIM_CITY))
        #write_table(dim_city,"gold","dim_city")
        first,last = fact_city_year.agg(F.min("year"),F.max("year")).first()
        dim_year = build_dim_year(first,last,spark)
        #dim_year.write.mode("overwrite").parquet(str(GOLD_DIM_YEAR))
        write_table(dim_year,"gold","dim_year")
        log.info(f"gold written: fact_cooling_hours {fact_cooling_hours.count()} rows, fact_city_year {fact_city_year.count()} rows")
        log.info(f"gold run finished: SUCCESS ({time.perf_counter()- t0:.1f} s)")
    except Exception:
        log.exception("gold run FAILED")
        raise
    finally:
        if silver is not None:
            silver.unpersist()
            
if __name__ == "__main__":
    build_gold()
    
    