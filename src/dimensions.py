from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from paths import CITIES_ALL_FILE, CITIES_WATER_STRESS, DIM_MODE, DIM_SCENARIO


def build_dim_mode(spark: SparkSession) -> DataFrame:
    dim_mode = spark.read.csv(
        str(DIM_MODE),
        header=True,
        schema="mode STRING,label STRING, "
        "uses_water BOOLEAN, uses_chiller BOOLEAN, "
        "color STRING, sort_order INT",
        enforceSchema=False,
    )
    return dim_mode


def build_dim_scenario(spark: SparkSession) -> DataFrame:
    dim_scenario = spark.read.csv(
        str(DIM_SCENARIO),
        header=True,
        schema="scenario STRING,sort_order INT,"
        "label STRING,cooling_type STRING, "
        "design STRING, evap_assist BOOLEAN, "
        "A DOUBLE, dew_max DOUBLE, dew_min DOUBLE, "
        "eps_evap DOUBLE, eps_hx DOUBLE, T_return DOUBLE, "
        "description STRING, source STRING",
        enforceSchema=False,
    )
    return dim_scenario


def build_dim_city(spark: SparkSession) -> DataFrame:
    cities = spark.read.csv(
        str(CITIES_ALL_FILE),
        header=True,
        schema="city STRING,"
        "name STRING,"
        "country STRING,"
        "admin1 STRING,"
        "region STRING,"
        "cw_region STRING,"
        "regulatory_zone STRING,"
        "scope STRING,"
        "my_group STRING,"
        "cw2026_tier STRING,"
        "cw2026_rank DOUBLE,"
        "active BOOLEAN,"
        "reason STRING,"
        "lat DOUBLE,"
        "lon DOUBLE,"
        "timezone STRING,"
        "country_name STRING,"
        "admin1_found STRING,"
        "climate_class STRING,"
        "climate_description STRING",
        enforceSchema=False,
    )
    bws = spark.read.csv(
        str(CITIES_WATER_STRESS),
        header=True,
        schema="city STRING,"
        "pfaf_id INT,"
        "bws_annual_score DOUBLE,"
        "bws_annual_cat INT,"
        "bws_annual_label STRING,"
        "bws_months_ge_4 INT",
        enforceSchema=False,
    )
    dim_city = cities.join(bws, on="city", how="left")
    return dim_city


def build_dim_year(first: int, last: int, spark: SparkSession) -> DataFrame:
    years = (
        spark.range(first, last + 1)
        .withColumnRenamed("id", "year")
        .withColumn("year", F.col("year").cast("int"))
    )

    decade_start = ((F.floor(F.col("year") / 10)) * 10).cast("int")
    decade = F.concat(decade_start.cast("string"), F.lit("s"))

    # WMO reference periods (between includes both ends)
    period = (
        F.when(F.col("year") < 1961, "before 1961")
        .when(F.col("year").between(1961, 1990), "1961-1990")
        .when(F.col("year").between(1991, 2020), "1991-2020")
        .otherwise("recent")
    )
    return (
        years.withColumn("decade", decade)
        .withColumn("reference_period", period)
        .orderBy("year")
    )


if __name__ == "__main__":
    build_dim_year()
