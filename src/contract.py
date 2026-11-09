EXPECT_FIELDS = ("time", "temperature_2m", "relative_humidity_2m", "dew_point_2m")
ROW_RULES = {
    "DQ-06a": "temperature_2m IS NOT NULL",
    "DQ-06b": "dew_point_2m IS NOT NULL",
    "DQ-06c": "relative_humidity_2m IS NOT NULL",
    "DQ-07":  "relative_humidity_2m BETWEEN 0 AND 100",
    "DQ-08":  "temperature_2m BETWEEN -50 AND 55",
    "DQ-09":  "dew_point_2m <= temperature_2m"
}