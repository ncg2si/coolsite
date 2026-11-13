import pytest
from pyspark.sql import functions as F

from spark_utils import get_spark
from classify import classify, DEFAULT_PARAMS

@pytest.fixture(scope="module")
def spark():
    return get_spark()

def make_table(spark):
    return spark.createDataFrame([(20.0,15.0,10.0,"free","free","free","free"), # cool → free
                                     (32.0,20.0,12.0,"evaporative","evaporative","evaporative","evaporative"), # hot but dry → evaporative
                                     (38.0,30.0,14.0,"hybrid","chiller","hybrid","chiller"), # very hot → hybrid / chiller
                                     (25.0,22.0,18.0,"chiller","chiller","evaporative","evaporative"), # humid: direct → chiller, indirect → evaporative
                                     (-15.0,-16.0,-20.0,"free","free","free","free")]                  # very cold and dry → free + too_dry              
                                    , ["temperature_c","wet_bulb_c",
                                       "dew_point_c","direct_hybrid_allowed",
                                       "direct_hybrid_not_allowed","indirect_hybrid_allowed",
                                       "indirect_hybrid_not_allowed"]
                                       )


@pytest.mark.parametrize("design, evap_assist, expected_col", [
    ("direct",   True,  "direct_hybrid_allowed"),
    ("direct",   False, "direct_hybrid_not_allowed"),
    ("indirect", True,  "indirect_hybrid_allowed"),
    ("indirect", False, "indirect_hybrid_not_allowed"),])

def test_cooling_mode(spark,design,evap_assist,expected_col):
    df = make_table(spark)
    classified_df = classify(df,design, {**DEFAULT_PARAMS,"evap_assist" : evap_assist})
    mismatches = classified_df.filter(F.col("mode") != F.col(expected_col))
    assert mismatches.count() == 0


def test_humidity_limited_direct(spark):
    result = classify(make_table(spark), "direct")
    flagged = result.filter(F.col("humidity_limited"))
    assert flagged.count() == 1
    assert flagged.first()["temperature_c"] == 25.0

def test_too_dry_direct(spark):
    result = classify(make_table(spark), "direct")
    flagged = result.filter(F.col("too_dry"))
    assert flagged.count() == 1
    assert flagged.first()["temperature_c"] == -15.0


def test_no_flags_indirect(spark):
    result = classify(make_table(spark), "indirect")
    flagged = result.filter(F.col("humidity_limited") | F.col("too_dry"))
    assert flagged.count() == 0