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


# ---------- degree-hours (water_degree, chiller_degree) ----------
# Expected values per row of make_table, for each design / evap_assist combination.
# a = 27 (direct); a_ind = T_return - (T_return - A) / eps_hx ≈ 22.714 (indirect).
A = DEFAULT_PARAMS["A"]
A_IND = DEFAULT_PARAMS["T_return"] - (DEFAULT_PARAMS["T_return"] - A) / DEFAULT_PARAMS["eps_hx"]

EXPECTED_DEG = {
    # (design, evap_assist): [(water_degree, chiller_degree) for rows 1..5 of make_table]
    ("direct", True):    [(0, 0), (32 - A, 0), (6.4, 31.6 - A), (0, 0), (0, 0)],
    ("direct", False):   [(0, 0), (32 - A, 0), (0, 38 - A),     (0, 0), (0, 0)],
    ("indirect", True):  [(0, 0), (32 - A_IND, 0), (6.4, 31.6 - A_IND), (25 - A_IND, 0), (0, 0)],
    ("indirect", False): [(0, 0), (32 - A_IND, 0), (0, 38 - A_IND),     (25 - A_IND, 0), (0, 0)],
}


@pytest.mark.parametrize("design, evap_assist", list(EXPECTED_DEG))
def test_degree_hours(spark, design, evap_assist):
    result = classify(make_table(spark), design, {**DEFAULT_PARAMS, "evap_assist": evap_assist}).collect()
    by_temp = {r["temperature_c"]: (r["water_degree"], r["chiller_degree"]) for r in result}
    expected = dict(zip([20.0, 32.0, 38.0, 25.0, -15.0], EXPECTED_DEG[(design, evap_assist)]))
    for temp, (water, chiller) in expected.items():
        assert by_temp[temp][0] == pytest.approx(water, abs=1e-6), f"water_degree at T={temp}"
        assert by_temp[temp][1] == pytest.approx(chiller, abs=1e-6), f"chiller_degree at T={temp}"


@pytest.mark.parametrize("design", ["direct", "indirect"])
def test_degree_hours_add_up(spark, design):
    """Property: when outside air is usable, water + chiller = T - a (the whole cooling job)."""
    a = A if design == "direct" else A_IND
    rows = (classify(make_table(spark), design)
            .filter((F.col("mode") != "free") & ~F.col("humidity_limited"))
            .collect())
    assert rows, "test table should contain non-free rows"
    for r in rows:
        assert r["water_degree"] + r["chiller_degree"] == pytest.approx(r["temperature_c"] - a, abs=1e-6)


@pytest.mark.parametrize("design", ["direct", "indirect"])
def test_degree_hours_never_negative(spark, design):
    result = classify(make_table(spark), design)
    assert result.filter((F.col("water_degree") < 0) | (F.col("chiller_degree") < 0)).count() == 0
