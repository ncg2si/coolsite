from aggregate import add_coverage

from spark_utils import get_spark
import pytest

@pytest.fixture(scope="module")
def spark():
    return get_spark()

def test_coverage(spark):
    df = spark.createDataFrame(
        [(2023, 8760), (2024, 8784), (2024, 8760)],
        ["year", "total_hours"]
    )
    result = add_coverage(df).orderBy("year","total_hours").collect()
    #print (result)
    assert not result[0]["incomplete"] 
    assert result[1]["incomplete"]  == True
    assert not result[2]["incomplete"]  
    assert result[2]["expected_hours"] == 8784