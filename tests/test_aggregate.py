from aggregate import add_coverage

from spark_utils import get_spark
import pytest
from pyspark.sql import SparkSession, functions as F
from aggregate import count_modes
from classify import DEFAULT_PARAMS

@pytest.fixture(scope="module")
def spark():
    return get_spark()

def test_coverage(spark: SparkSession):
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


def make_hours(spark):
    """5 hours of one city year """
    #city, year, t, t_wetbulb, dew_point
    return spark.createDataFrame(
    [("testcity", 2025, 20.0, 15.0, 10.0), # cool - free
     ("testcity", 2025, 32.0, 20.0, 12.0), # hot, dry - evaporative
     ("testcity", 2025, 25.0, 22.0, 18.0), # cool, humid - direct:chiller (too humid) 
     ("testcity", 2025, 30.0, 26.0, 24.0), # hot, humid - direct: chiller (too humid)
     ("testcity", 2025, 48.0, 25.0, 15.0), # desert: hot but dry - direct: hybrid   
    ],
    ["city", "year", "temperature_c", "wet_bulb_c", "dew_point_c"],
    ) 

def scenario(name, design, evap_assist):
    """ Fixed default parameter """
    return {**DEFAULT_PARAMS, "scenario": name, "design":design, "evap_assist": evap_assist}

SCENARIOS = [
    scenario("t_direct","direct",True),
    scenario("t_direct_no_hybrid", "direct", False),
    scenario("t_indirect","indirect",True),
    scenario("t_indirect_no_hybrid","indirect", False)
]


def by_mode(spark,s):
    return {r["mode"]: r for r in count_modes(make_hours(spark),s).collect()}

@pytest.mark.parametrize("s", SCENARIOS, ids=lambda s: s["scenario"])
def test_zero_rules(spark, s):
    """free uses nothing; evaporative uses no chiller; chiller uses no water."""
    rows = by_mode(spark, s)
    if "free" in rows:
        assert rows["free"]["water_degree_hours"] == 0
        assert rows["free"]["chiller_degree_hours"] == 0
    if "evaporative" in rows:
        assert rows["evaporative"]["chiller_degree_hours"] == 0
    if "chiller" in rows:
        assert rows["chiller"]["water_degree_hours"] == 0


@pytest.mark.parametrize("s", SCENARIOS, ids=lambda s: s["scenario"])
def test_hours_add_up(spark, s):
    """Every input hour lands in exactly one mode."""
    rows = by_mode(spark, s)
    assert sum(r["hours"] for r in rows.values()) == 5


def test_direct_with_hybrid_every_chiller_hour_is_humidity(spark):
    rows = by_mode(spark, SCENARIOS[0])
    assert rows["chiller"]["hours"] == 2
    assert rows["chiller"]["humidity_limited_hours"] == 2
    assert rows["hybrid"]["hours"] == 1                 # the desert hour


def test_direct_no_hybrid_desert_hour_is_heat_not_humidity(spark):
    rows = by_mode(spark, SCENARIOS[1])
    assert "hybrid" not in rows
    assert rows["chiller"]["hours"] == 3
    assert rows["chiller"]["humidity_limited_hours"] == 2   # chiller > humidity


def test_humid_cool_hour_adds_no_chiller_degree(spark):
    """Limitation made visible: hour 3 runs the chiller but adds 0 K·h; only hour 4 (30 °C) counts."""
    rows = by_mode(spark, SCENARIOS[0])
    assert rows["chiller"]["chiller_degree_hours"] == pytest.approx(30.0 - DEFAULT_PARAMS["A"])


def test_indirect_never_humidity_limited(spark):
    rows = by_mode(spark, SCENARIOS[2])
    assert sum(r["humidity_limited_hours"] for r in rows.values()) == 0


def test_indirect_no_hybrid_hot_hours_become_chiller(spark):
    """Hours 4 and 5 are too hot for evaporative alone: hybrid when allowed, otherwise chiller - never humidity."""
    with_hybrid = by_mode(spark, SCENARIOS[2])
    no_hybrid = by_mode(spark, SCENARIOS[3])
    assert with_hybrid["hybrid"]["hours"] == 2
    assert "chiller" not in with_hybrid
    assert "hybrid" not in no_hybrid
    assert no_hybrid["chiller"]["hours"] == 2
    assert no_hybrid["chiller"]["humidity_limited_hours"] == 0