"""Machine-readable part of docs/data_contract.md. Change both together and raise the version."""

CONTRACT_VERSION = "0.7.0"

WEATHER_MODEL = "era5_land"
# Structural (DQ-01): fields every bronze file must have
EXPECT_FIELDS = ("time", "temperature_2m", "relative_humidity_2m", "dew_point_2m")

COLUMN_MAP = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "humidity_pct",
    "dew_point_2m": "dew_point_c"
}

# Structural (DQ-02): timezone of the raw response
EXPECT_TIMEZONE = "GMT"

# Row rules (DQ-06..09): SQL condition a VALID row must satisfy.
# A row that breaks one or more rules is quarantined with the rule IDs.
DEW_POINT_TOLERANCE_C = 0.1     # API values are rounded to 0.1 °C
ROW_RULES = {
    "DQ-06a": "temperature_c IS NOT NULL",
    "DQ-06b": "dew_point_c IS NOT NULL",
    "DQ-06c": "humidity_pct IS NOT NULL",
    "DQ-07":  "humidity_pct BETWEEN 0 AND 100",
    "DQ-08":  "temperature_c BETWEEN -50 AND 55",   # provisional, see contract
    "DQ-09":  f"ROUND(dew_point_c - temperature_c,1)<= {DEW_POINT_TOLERANCE_C}",      # DEW_POINT_TOLERANCE_C °C tolerance
}

# Severity policy (contract section 3)
MAX_UNUSABLE_HOURS_PER_FILE = 2      # more → error, run fails
MIN_COVERAGE_CITY_YEAR = 0.999       # less → city-year marked "incomplete" in gold


WET_BULB_TOLERANCE_C = 1.0 # Stull (2011) published error: -1 to +0.65 °C
SILVER_CONSTRAINTS = {
    "key_city_not_null": "city IS NOT NULL",
    "key_time_not_null": "time IS NOT NULL",
    **{rule_id.lower().replace("-","_"): rule for rule_id, rule in ROW_RULES.items()}, # DQ-06a -> dq_06a
    "wet_bulb_plausible":(f"wet_bulb_c <= temperature_c + {WET_BULB_TOLERANCE_C} AND wet_bulb_c >= dew_point_c - {WET_BULB_TOLERANCE_C}")
}

