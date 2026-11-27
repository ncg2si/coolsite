from pyspark.sql import functions as F

from contract import SILVER_CONSTRAINTS
from paths import ON_DATABRICKS
from spark_utils import get_spark
from storage import read_table, table_name


def apply_silver_constraints(spark) -> None:
    table = table_name("silver", "weather_hourly")
    for name, rule in SILVER_CONSTRAINTS.items():
        spark.sql(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
        spark.sql(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({rule})")


def count_violations(spark) -> dict:
    df = read_table(spark, "silver", "weather_hourly")
    checks = [
        F.count_if(~F.expr(rule)).alias(name)
        for name, rule in SILVER_CONSTRAINTS.items()
    ]
    return df.agg(*checks).first().asDict()


if __name__ == "__main__":
    # only on Databricks
    if not ON_DATABRICKS:
        print(
            "Run this on Databricks - Constraints need a Delta table in Unity Catalog"
        )
    else:
        spark = get_spark()
        table = table_name("silver", "weather_hourly")
        violations = count_violations(spark)
        failed = {rule: n for rule, n in violations.items() if n > 0}
        if failed:
            for rule, count in failed.items():
                print(f"Rule {rule} violated : {count} rows")
            raise ValueError(f"Silver violates {len(failed)} constraint(s): {failed}")
        apply_silver_constraints(spark)
        (
            spark.sql(f"SHOW TBLPROPERTIES {table}")
            .filter("key LIKE 'delta.constraints.%'")
            .show(truncate=False)
        )
