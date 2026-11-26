from pyspark.sql import functions as F

from contract import SILVER_CONSTRAINTS
from storage import read_table, table_name


def apply_silver_constraints(spark) -> None:
    table = table_name("silver","weather_hourly")
    for name, rule in SILVER_CONSTRAINTS.items():
        spark.sql(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
        spark.sql(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({rule})")
    

def count_violations(spark) -> dict:
    df = read_table(spark,"silver","weather_hourly")
    checks = [F.count_if(~F.expr(rule)).alias(name) for name, rule in SILVER_CONSTRAINTS.items()]
    return df.agg(*checks).first().asDict()


# def count_violations(spark) -> dict:
#     df = read_table(spark,"silver","weather_hourly")
#     row = (df.agg(
#         F.count_if((F.col("temperature_c")>55)|(F.col("temperature_c")<-50)).alias("n_temp_out_of_range"),
#         F.count_if((F.col("humidity_pct")>100)|(F.col("humidity_pct")<0)).alias("n_humidity_out_of_range"),
#         F.count_if(F.round(F.col("dew_point_c")-F.col("temperature_c"),1)>0.1).alias("n_dew_above_temp"),
#         F.count_if((F.col("wet_bulb_c") > F.col("temperature_c") + WET_BULB_TOLERANCE_C)
#              | (F.col("wet_bulb_c") < F.col("dew_point_c") - WET_BULB_TOLERANCE_C)).alias("n_wb_implausible"),     
#     ).first())
#     return row.asDict()