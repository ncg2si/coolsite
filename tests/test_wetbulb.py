import pytest
from pyspark.sql import functions as F

from spark_utils import get_spark
from utils.wetbulb import wet_bulb_stull

@pytest.fixture(scope="module")
def spark():
    return get_spark()

def test_stull_example_from_paper(spark):
    # a dataframe with 1 row, 2 column t and rh
    df = spark.createDataFrame([(20.0, 50.0)], ["t","rh"])

    # add the column wetbulb "tw"
    result = df.withColumn("tw",wet_bulb_stull(F.col("t"),F.col("rh")))

    # test
    tw = result.collect()[0]["tw"]
    assert tw == pytest.approx(13.70, abs=0.05)