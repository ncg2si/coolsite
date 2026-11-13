"""Machine-readable part of docs/data_contract.md. Change both together and raise the version."""

CONTRACT_VERSION = "0.5"

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
ROW_RULES = {
    "DQ-06a": "temperature_c IS NOT NULL",
    "DQ-06b": "dew_point_c IS NOT NULL",
    "DQ-06c": "humidity_pct IS NOT NULL",
    "DQ-07":  "humidity_pct BETWEEN 0 AND 100",
    "DQ-08":  "temperature_c BETWEEN -50 AND 55",   # provisional, see contract
    "DQ-09":  "dew_point_c <= temperature_c",      # 0 °C tolerance
}

# Severity policy (contract section 3)
MAX_UNUSABLE_HOURS_PER_FILE = 2      # more → error, run fails
MIN_COVERAGE_CITY_YEAR = 0.999       # less → city-year marked "incomplete" in gold
