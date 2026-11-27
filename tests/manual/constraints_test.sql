-- =====================================================================
-- Manual test of the Delta CHECK constraints on silver.weather_hourly
-- Contract 0.7.0 · constraints added by src/constraints.py
--
-- HOW TO RUN (SQL Editor, warehouse coolsite-wh):
--   1. Run section 0 and check: exactly 9 rows delta.constraints.* on the clone.
--   2. Run each INSERT ONE BY ONE (select it, Cmd+Enter), not "Run all":
--      "Run all" stops at the first blocked INSERT.
--   3. Run section 7: expect exactly 8 rows (the SUCCESS tests).
--   4. Run section 8: clean up.
--
-- RULE OF THUMB: each test changes ONE value of the valid baseline row,
-- so only one rule can fail. Exception: NULL tests (Delta treats a NULL
-- check result as a violation, so one NULL breaks several rules).
-- =====================================================================

USE CATALOG dbw_coolsite_7405619082079658;

-- ===== 0. Setup: shallow clone (no data copied, the real table is never touched)
CREATE SCHEMA IF NOT EXISTS sandbox;
CREATE OR REPLACE TABLE sandbox.weather_hourly SHALLOW CLONE silver.weather_hourly;
SHOW TBLPROPERTIES sandbox.weather_hourly;   -- STOP if not 9 delta.constraints.* rows


-- ===== 1. Baseline: a fully valid row
-- check: dew 14 <= 20.1 | wet-bulb 16 <= 21 and >= 13
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 00:00:00', 20.0, 70, 14.0, 16.0);


-- ===== 2. NULL values (one NULL breaks several rules)
-- temperature NULL
-- expect: blocked (dq_06a, dq_08, dq_09, wet_bulb_plausible, column NOT NULL)
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 01:00:00', NULL, 70, 14.0, 16.0);

-- humidity NULL
-- expect: blocked (dq_06c, dq_07, column NOT NULL)
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 02:00:00', 20.0, NULL, 14.0, 16.0);

-- dew point NULL
-- expect: blocked (dq_06b, dq_09, wet_bulb_plausible, column NOT NULL)
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 03:00:00', 20.0, 70, NULL, 16.0);

-- city NULL
-- expect: blocked (key_city_not_null, column NOT NULL)
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES (NULL, TIMESTAMP'2001-01-01 04:00:00', 20.0, 70, 14.0, 16.0);

-- time NULL
-- expect: blocked (key_time_not_null, column NOT NULL)
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', NULL, 20.0, 70, 14.0, 16.0);


-- ===== 3. dq_07: humidity 0 to 100 %
-- too high
-- expect: blocked by dq_07
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 06:00:00', 20.0, 150, 14.0, 16.0);

-- negative
-- expect: blocked by dq_07
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 07:00:00', 20.0, -5, 14.0, 16.0);

-- boundary: exactly 100 % (saturation: all three temperatures equal)
-- check: dew 15 <= 15.1 | wet-bulb 15 <= 16 and >= 14
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 08:00:00', 15.0, 100, 15.0, 15.0);

-- boundary: exactly 0 % (valid by the rules, not by physics: rules only check what they say)
-- check: dew -40 <= 30.1 | wet-bulb 10 <= 31 and >= -41
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 09:00:00', 30.0, 0, -40.0, 10.0);


-- ===== 4. dq_08: temperature -50 to 55 °C
-- too hot
-- check: dew 40 <= 60.1 | wet-bulb 45 <= 61 and >= 39
-- expect: blocked by dq_08
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 10:00:00', 60.0, 30, 40.0, 45.0);

-- too cold
-- check: dew -63 <= -59.9 | wet-bulb -61 <= -59 and >= -64
-- expect: blocked by dq_08
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 11:00:00', -60.0, 70, -63.0, -61.0);

-- boundary: exactly 55 °C (BETWEEN includes both ends)
-- check: dew 25 <= 55.1 | wet-bulb 32 <= 56 and >= 24
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 12:00:00', 55.0, 20, 25.0, 32.0);

-- boundary: exactly -50 °C
-- check: dew -53 <= -49.9 | wet-bulb -51 <= -49 and >= -54
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 13:00:00', -50.0, 70, -53.0, -51.0);


-- ===== 5. dq_09: dew point <= temperature + 0.1 °C (difference rounded to 0.1)
-- dew point 0.5 °C above temperature, wet-bulb still plausible
-- check: wet-bulb 20 <= 21 and >= 19.5
-- expect: blocked by dq_09
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 14:00:00', 20.0, 100, 20.5, 20.0);

-- boundary: dew point exactly 0.1 above temperature (API rounding, Stockholm 2024 case)
-- without ROUND, 1.6 - 1.5 = 0.10000000000000009 > 0.1 would be blocked by mistake
-- check: wet-bulb 1.5 <= 2.5 and >= 0.6
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 15:00:00', 1.5, 100, 1.6, 1.5);


-- ===== 6. wet_bulb_plausible: dew point - 1 <= wet-bulb <= temperature + 1
-- wet-bulb 2 °C above temperature
-- expect: blocked by wet_bulb_plausible
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 16:00:00', 20.0, 70, 14.0, 22.0);

-- wet-bulb 2 °C below dew point
-- expect: blocked by wet_bulb_plausible
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 17:00:00', 20.0, 70, 14.0, 12.0);

-- boundary: wet-bulb exactly 1.0 above temperature
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 18:00:00', 20.0, 70, 14.0, 21.0);

-- boundary: wet-bulb exactly 1.0 below dew point
-- expect: SUCCESS
INSERT INTO sandbox.weather_hourly (city, time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c)
VALUES ('test', TIMESTAMP'2001-01-01 19:00:00', 20.0, 70, 14.0, 13.0);


-- ===== 7. Results
-- expect: exactly 8 rows, at 00, 08, 09, 12, 13, 15, 18, 19 o'clock
SELECT time, temperature_c, humidity_pct, dew_point_c, wet_bulb_c
FROM sandbox.weather_hourly
WHERE city = 'test'
ORDER BY time;

-- safety check: the real table was never touched -> expect 0 rows
SELECT COUNT(*) AS test_rows_in_real_silver
FROM silver.weather_hourly
WHERE city = 'test';


-- ===== 8. Clean up
DROP TABLE IF EXISTS sandbox.weather_hourly;