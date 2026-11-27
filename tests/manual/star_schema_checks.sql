-- ================================================================
-- Gold checks: invariants between silver and gold
-- Run: SQL Editor, coolsite-wh, after build_gold()
-- Convention: every query looks for VIOLATIONS -> expect 0 rows
-- ================================================================

-- ===== Set up =====

USE CATALOG dbw_coolsite_7405619082079658;

-- ===== 1. Check uniqueness =====
-- --- Expect: 0 rows
-- --- 1.a Unique keys in fact_cooling_hours
SELECT city,year,scenario,mode, COUNT(*) AS n
FROM gold.fact_cooling_hours
GROUP BY city,year,scenario, mode
HAVING COUNT(*) > 1;

-- --- 1.b Unique keys in fact_city_year
SELECT city,year, COUNT(*) AS n
FROM gold.fact_city_year
GROUP BY city,year
HAVING COUNT(*) > 1;

-- --- 1.c Unique keys in dim_scenario
SELECT scenario, COUNT(*) AS n
FROM gold.dim_scenario
GROUP BY scenario
HAVING COUNT(*) > 1;
-- --- 1.d Unique keys in dim_city
SELECT city, COUNT(*) AS n
FROM gold.dim_city
GROUP BY city
HAVING COUNT(*) > 1;

-- --- 1.e  Unique keys in dim_mode
SELECT mode, COUNT(*) AS n
FROM gold.dim_mode
GROUP BY mode
HAVING COUNT(*) >1;

-- --- 1.f Unique keys in dim_year
SELECT year, COUNT(*) AS n
FROM gold.dim_year
GROUP BY year
HAVING COUNT(*) > 1;

-- ===== 2. Check completeness =====
-- --- Expect: 0 rows
-- --- 2.a no extra city-year in gold fact_city_year that is not in silver
WITH s AS (
    SELECT DISTINCT city,year 
    FROM silver.weather_hourly)
SELECT g.city, g.year
FROM gold.fact_city_year AS g
LEFT JOIN s ON g.city = s.city AND g.year = s.year
WHERE s.city IS NULL;

-- --- 2.b no missing city-year in gold fact_city_year 
WITH s AS (
  SELECT DISTINCT city, year
  FROM silver.weather_hourly)
SELECT s.city, s.year
FROM s 
LEFT JOIN gold.fact_city_year AS g ON g.city = s.city AND g.year = s.year
WHERE g.city IS NULL;

-- --- 2.c no extra city-year-scenario in gold fact_cooling_hours  (that is not in silver x dim_scenario)

WITH s AS (
    SELECT DISTINCT city,year
    FROM silver.weather_hourly
),
es AS (
    SELECT s.city,s.year,sc.scenario
    FROM s
    CROSS JOIN gold.dim_scenario AS sc
)
SELECT DISTINCT g.city, g.year, g.scenario
FROM gold.fact_cooling_hours AS g
LEFT JOIN es ON g.city = es.city AND g.year = es.year AND g.scenario = es.scenario
WHERE es.city IS NULL;

-- --- 2.d no missing city-year-scenario in gold fact_cooling_hours  (in silver x dim_scenario)

WITH s AS (
    SELECT DISTINCT city,year
    FROM silver.weather_hourly
),
es AS (
    SELECT s.city,s.year,sc.scenario
    FROM s
    CROSS JOIN gold.dim_scenario AS sc
)
SELECT DISTINCT es.city, es.year, es.scenario
FROM es
LEFT JOIN gold.fact_cooling_hours as g ON g.city = es.city AND g.year = es.year AND g.scenario = es.scenario
WHERE g.city IS NULL;


-- ===== 3. Check Balance  =====
-- --- 3.a Every silver hour lands in exactly one mode, per scenario 
-- --- expect : 0 rows
WITH s AS (
SELECT city, year, COUNT(*) AS silver_hours
FROM silver.weather_hourly
GROUP BY city,year),
g AS(
SELECT city,year,scenario, SUM(hours) AS gold_hours
FROM gold.fact_cooling_hours
GROUP BY city,year,scenario)
SELECT g.city, g.year, g.scenario, g.gold_hours, s.silver_hours
FROM g
JOIN s ON g.city = s.city AND g.year = s.year 
WHERE g.gold_hours <> s.silver_hours;

-- --- 3.b degree-hours: water + chiller degree-hours = SUM(max(T - a, 0)) from silver
-- ---     (the classification only splits the cooling demand, it never creates or loses it)
-- --- expect: 0 rows
WITH thr AS (
    SELECT scenario,
           CASE WHEN design = 'direct' THEN A
                ELSE T_return - (T_return - A) / eps_hx
           END AS a
    FROM gold.dim_scenario
),
s AS (
    SELECT w.city, w.year, t.scenario,
           SUM(GREATEST(w.temperature_c - t.a, 0)) AS silver_degree_hours
    FROM silver.weather_hourly AS w
    CROSS JOIN thr AS t
    GROUP BY w.city, w.year, t.scenario
),
g AS (
    SELECT city, year, scenario,
           SUM(water_degree_hours + chiller_degree_hours) AS gold_degree_hours
    FROM gold.fact_cooling_hours
    GROUP BY city, year, scenario
)
SELECT g.city, g.year, g.scenario, g.gold_degree_hours, s.silver_degree_hours
FROM g
JOIN s ON g.city = s.city AND g.year = s.year AND g.scenario = s.scenario
WHERE ABS(g.gold_degree_hours - s.silver_degree_hours) > 0.01;

-- ===== 4. Referential integrity (fact -> dim) =====
-- --- expect : 0 rows
-- --- 4.a every mode in fact_cooling_hours exists in dim_mode

SELECT DISTINCT f.mode 
FROM gold.fact_cooling_hours AS f
LEFT JOIN gold.dim_mode AS m ON f.mode = m.mode
WHERE m.mode IS NULL;

-- --- 4.b every scenario in fact_cooling_hours exists in dim_scenario

SELECT DISTINCT f.scenario 
FROM gold.fact_cooling_hours AS f
LEFT JOIN gold.dim_scenario AS s ON f.scenario = s.scenario
WHERE s.scenario IS NULL;

-- --- 4.c every city in fact_cooling_hours exists in dim_city

SELECT DISTINCT f.city 
FROM gold.fact_cooling_hours AS f
LEFT JOIN gold.dim_city AS c ON f.city = c.city
WHERE c.city IS NULL;

-- --- 4.d every year in fact_cooling_hours exists in dim_year

SELECT DISTINCT f.year 
FROM gold.fact_cooling_hours AS f
LEFT JOIN gold.dim_year AS y ON f.year = y.year
WHERE y.year IS NULL;

-- --- 4.e every city in fact_city_year exists in dim_city

SELECT DISTINCT f.city 
FROM gold.fact_city_year AS f
LEFT JOIN gold.dim_city AS c ON f.city = c.city
WHERE c.city IS NULL;

-- --- 4.f every year in fact_city_year exists in dim_year

SELECT DISTINCT f.year 
FROM gold.fact_city_year AS f
LEFT JOIN gold.dim_year AS y ON f.year = y.year
WHERE y.year IS NULL;

