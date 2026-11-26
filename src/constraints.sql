-- To run on Databricks 
USE CATALOG dbw_coolsite_7405619082079658; 
-- Check for violation

SELECT COUNT(*) FROM silver.weather_hourly
WHERE NOT (temperature_c BETWEEN  -50 AND 55);
SELECT COUNT(*) FROM silver.weather_hourly
WHERE NOT (humidity_pct BETWEEN 0 AND 100);
SELECT COUNT(*) FROM silver.weather_hourly
WHERE NOT (ROUND(dew_point_c-temperature_c,1) <= 0.1);


-- 1. Column constraints NOT NULL
ALTER TABLE silver.weather_hourly ALTER COLUMN city SET NOT NULL;
ALTER TABLE silver.weather_hourly ALTER COLUMN time SET NOT NULL;
ALTER TABLE silver.weather_hourly ALTER COLUMN temperature_c SET NOT NULL;
ALTER TABLE silver.weather_hourly ALTER COLUMN humidity_pct SET NOT NULL;
ALTER TABLE silver.weather_hourly ALTER COLUMN dew_point_c SET NOT NULL;

--2. Table constraints: CHECK
ALTER TABLE silver.weather_hourly DROP CONSTRAINT IF EXISTS temperature_range;
ALTER TABLE silver.weather_hourly ADD CONSTRAINT temperature_range CHECK (temperature_c BETWEEN -50 AND 55);

ALTER TABLE silver.weather_hourly DROP CONSTRAINT IF EXISTS humidity_range;
ALTER TABLE silver.weather_hourly ADD CONSTRAINT humidity_range CHECK (humidity_pct BETWEEN 0 AND 100);

ALTER TABLE silver.weather_hourly DROP CONSTRAINT IF EXISTS dew_point_le_temperature;
ALTER TABLE silver.weather_hourly ADD CONSTRAINT dew_point_le_temperature CHECK ((ROUND(dew_point_c-temperature_c,1)) <= 0.1 ); --DEW_POINT_TOLERANCE_C = 0.1

--3. Verify
SHOW TBLPROPERTIES silver.weather_hourly;
DESCRIBE TABLE silver.weather_hourly;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'silver' AND table_name = 'weather_hourly'
ORDER BY ordinal_position;


-- 4. POST-LOAD CHECK: wet-bulb plausibility (warning only, not a constraint)
-- Rule: dew point <= wet-bulb <= air temperature.
-- wet_bulb_c is derived with Stull (2011): valid for 5-99 % RH and -20 to 50 C
-- at 1013.25 hPa, error -1 to +0.65 C (mean absolute error < 0.3 C).
-- Result 2026-11-26 (13.1 M hours): 328 hours with wet-bulb > air temperature,
-- all explained (humidity > 95 % or temperature < 0 C, 0 unexplained), max 0.14 C.
-- Within the formula error; cold hours are free cooling anyway -> no cooling mode changes.
-- Still open: 225,717 hours with wet-bulb < dew point (max 0.24 C) -> under investigation.
SELECT 
-- SUM(CASE WHEN wet_bulb_c > temperature_c THEN 1 ELSE 0 END)
    COUNT_IF(wet_bulb_c > temperature_c) AS wb_above_temp, 
    COUNT_IF(wet_bulb_c > temperature_c AND humidity_pct > 95) AS wb_above_temp_humid, --explain assumption for Stull formula only for rel humidity range 5%-99%
    COUNT_IF(wet_bulb_c > temperature_c AND temperature_c < 0) AS wb_above_temp_cold, --explain assumption for Stull formula not to apply when it is both dry and cold
    COUNT_IF(wet_bulb_c > temperature_c AND humidity_pct <= 95 AND temperature_c >= 0) AS wb_above_temp_unexplained
    COUNT_IF(wet_bulb_c < dew_point_c) AS wb_below_dew,
    MAX(wet_bulb_c - temperature_c) AS max_wb_above_temp,
    MAX(dew_point_c - wet_bulb_c ) AS max_wb_below_dw
FROM silver.weather_hourly;

SELECT MIN(humidity_pct), MAX(humidity_pct)
FROM silver.weather_hourly
WHERE wet_bulb_c > temperature_c AND temperature_c < 0 AND humidity_pct <= 95;
-- hours outside Stull's validated range
SELECT city,
    COUNT_IF (humidity_pct < 5) AS rh_below_5,
    COUNT_IF (humidity_pct > 99) AS rh_above_99,
    COUNT_IF (temperature_c < -20) AS temp_below_minus20,
    COUNT_IF (temperature_c > 50) AS temp_above_50
FROM silver.weather_hourly
GROUP BY city
ORDER BY city;
