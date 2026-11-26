# Data contract: Open-Meteo Historical Weather → CoolSite bronze

| | |
|---|---|
| Version | 0.7.0 (2026-11-26) |
| Producer | Open-Meteo Historical Weather API, model pinned to **ERA5-Land** (`models=era5_land`, 0.1° grid) |
| Consumer | CoolSite pipeline (transform → silver) |
| Owner | Cam Lai Ngo |
| Profiled with | notebooks/01_explore_api.ipynb: Frankfurt, 2026-06-01 → 2026-09-01 |

## 1. Schema
- Endpoint: https://archive-api.open-meteo.com/v1/archive
- Request: `models=era5_land` (pinned in src/contract.py as WEATHER_MODEL — without it the default "best match" mixes several models), `timezone=GMT`, hourly fields below
- Coordinates in the response snap to the ERA5-Land grid (0.1°), e.g. Frankfurt 50.11/8.68 → 50.10/8.70
- Storage: data/bronze/city=<city lowercase>/<start>.json, raw response, unchanged; backfill = one file per city × calendar year (`<start>` = YYYY-01-01)
- Structure: metadata on top (latitude, longitude, timezone, elevation);
  hourly values in data["hourly"] as equal-length lists (one list = one column)
- Grain: one row per city × hour

| field in bronze | column in silver | type in bronze | type in silver | unit | meaning |
|---|---|---|---|---|---|
| time | time | ISO text | timestamp, UTC | — | start of the hour |
| temperature_2m | temperature_c | float | float | °C | air temperature 2m above ground |
| dew_point_2m | dew_point_c | float | float | °C | dew point 2m above ground |
| relative_humidity_2m | humidity_pct | int | int | % | relative humidity 2m above ground |

- Source names are renamed to neutral names right after reading (COLUMN_MAP in src/contract.py), so row rules and later layers do not depend on the source

## 2. Quality rules (implemented in src/validate.py; IDs, fields and thresholds in src/contract.py)
| ID | Rule | Level | Severity / handling |
|---|---|---|---|
| DQ-01 | all expected fields present (schema drift check) | structural | missing field → always error, run stops · unexpected field → warning |
| DQ-02 | timezone = "GMT" (UTC) | structural | always error → run stops |
| DQ-03 | time range covers exactly start 00:00 → end 23:00 (both dates inclusive; values parsed as datetime, not compared as text) | dataset | hours missing at the start or end count as unusable → see severity policy · hours outside the range → warning, excluded from silver (they belong to another run) · exactly one city per file (city guard) |
| DQ-04 | no duplicate hours | dataset | identical duplicates → warning + remove the copies · conflicting duplicates (same hour, different values) → all copies go to quarantine with `failed_rules = ["DQ-04"]`; counted **once per hour** as unusable |
| DQ-05 | consecutive hours exactly 1 h apart (no gaps, no off-grid times) | dataset | missing whole hours count as unusable → see severity policy · off-grid steps (not a multiple of 1 h) are reported · runs before duplicate handling, so a removed conflicting hour is not counted twice |
| DQ-06 | no nulls in any field (DQ-06a temperature, DQ-06b dew point, DQ-06c humidity) | row | quarantine the row (counts as unusable) |
| DQ-07 | humidity 0–100 % | row | quarantine the row |
| DQ-08 | temperature -50 to 55 °C | row | quarantine the row |
| DQ-09 | dew point ≤ temperature + 0.1 °C tolerance (`DEW_POINT_TOLERANCE_C`); the difference is rounded to 0.1 °C before comparing | row | quarantine the row |

- DQ-08 provisional; refine after profiling extremes (Helsinki January, Athens July)
- DQ-09 Equality occurs only at 100 % humidity (saturation). The API rounds every value to 0.1 °C, so two rounded values can differ by up to 0.1 °C even when the true values are equal → tolerance 0.1 °C. First case: Stockholm 2024-02-22 04:00, temperature 1.5 °C, dew point 1.6 °C, RH 100 % (185 hours of that year have dew point exactly = temperature). The rule still catches real errors (dew point clearly above temperature). Implementation: `ROUND(dew_point_c - temperature_c, 1) <= 0.1` — without rounding, floating-point arithmetic makes e.g. 0.7 + 0.1 = 0.7999999999999999, so a dew point of exactly 0.8 was wrongly quarantined (seen in Reykjavik 1988-08-16 06:00 and Stockholm 1999-01-04 05:00, both at RH 100 %).
- The row count is not a rule of its own: if DQ-03, DQ-04 and DQ-05 pass, rows = days × 24 follows. It is logged as `rows_in`.
- Each problem has exactly one owning rule: edges of the range → DQ-03, duplicates → DQ-04, gaps inside the range → DQ-05.
- Order: DQ-01 and DQ-02 run first as a gate; if one fails the run stops at once (avoids follow-on errors, e.g. a shifted timezone also breaks DQ-03). Dataset and row rules all run, results are collected and decided together.

## 3. Severity policy
- **Unusable hours** = missing hours (DQ-03 at the edges / DQ-05 inside) + quarantined rows (DQ-06, DQ-07, DQ-08, DQ-09) + hours with conflicting duplicates (DQ-04)
- **Per run (each bronze file):** up to **2 unusable hours** → warning, the run continues; **more than 2** → error, the run fails
  (an absolute tolerance, because incremental files are small: one bad hour in a 7-day file is already 0.6 %)
- **Per city-year (gold):** a city-year is only used in comparisons if **≥ 99.9 %** of its expected hours are valid
  (at most **0.1 %** unusable ≈ 8–9 hours per year); otherwise it is marked `incomplete`
- **Metrics in gold are shares of valid hours** (e.g. free-cooling hours ÷ valid hours), and each city-year shows its coverage
- **Structural problems (DQ-01 missing field, DQ-02) are always errors**, independent of the tolerance
- Quarantined rows are kept with the IDs of the rules they broke — never deleted silently

## 3b. Silver table guarantees (Delta CHECK constraints)
Rules enforced **on the table** `silver.weather_hourly`: every write (backfill, incremental) that breaks fails as a whole and leaves the table unchanged. Applied by `src/constraints.py` (`apply_silver_constraints`):

| Constraint | Rule | Source |
|---|---|---|
| key_city_not_null, key_time_not_null | city, time not null | table key |
| dq_06a, dq_06b, dq_06c | temperature, dew point, humidity not null | = DQ-06 |
| dq_07 | humidity 0–100 % | = DQ-07 |
| dq_08 | temperature −50 to 55 °C | = DQ-08 |
| dq_09 | `ROUND(dew_point_c - temperature_c, 1) <= 0.1` | = DQ-09 |
| wet_bulb_plausible | dew point − 1 °C ≤ wet-bulb ≤ temperature + 1 °C (`WET_BULB_TOLERANCE_C`) | derived column |

- **wet_bulb_plausible** guards against code bugs in the calculation of wet-bulb, not against the source. Tolerance = 1 °C is published error of Stull, -1 to +0.65 °C. 

## 4. Freshness
- ERA5 / ERA5-Land arrive with ~5 days delay; the most recent days come from another model
  and may be revised → every run reloads the last 7 days (overwrite, idempotent)

## 5. Change handling
- New field in the response → log a warning. A new field doesn't harm the pipeline but an expected field missing or renamed does. 
- Expected field missing or renamed → DQ-01 fails → pipeline stops, bronze is kept
- Contract change → raise the version number, note it here

## 6. Change log
- 0.1 (2026-11-04): first version, from profiling Frankfurt (summer sample only)
- 0.2 (2026-11-09): severity policy added (2 unusable hours per file, 0.1 % per city-year); rules grouped by level (structural / dataset / row); DQ-03 split into identical vs conflicting duplicates; DQ-04 reworded — "increasing" dropped, because hours are sorted before the check (order in the raw file is not meaningful in Spark)
- 0.3 (2026-11-09): rules renumbered in the order they run (structural → dataset → row); no rule changed. Old → new: DQ-09→01, DQ-08→02, DQ-01→03, DQ-03→04, DQ-04→05, DQ-02→06, DQ-05→07, DQ-06→08, DQ-07→09
- 0.4 (2026-11-10): DQ-03 changed from row count to time range (first/last hour), so every problem has one owner; row count only logged; extra hours outside the range → warning + excluded; gate order documented; thresholds and IDs mirrored in src/contract.py (CONTRACT_VERSION)
- 0.5 (2026-11-13): model pinned to ERA5-Land (`models=era5_land`, 0.1° grid, coordinates snap to the grid); neutral column names in silver (temperature_c, humidity_pct, dew_point_c) via COLUMN_MAP; backfill stored as one bronze file per city × year; DQ-03 adds the one-city-per-file guard; DQ-04 conflicting duplicates → quarantine with rule ID, counted once per hour; DQ-05 off-grid steps reported, runs before duplicate handling; DQ-06 split into a/b/c per field
- 0.6 (2026-11-14): DQ-09 tolerance 0 → 0.1 °C (API rounding to 0.1 °C); found in the first real quarantine (Stockholm 2024-02-22 04:00: dew point 1.6 °C vs temperature 1.5 °C at RH 100 %); tolerance in src/contract.py as DEW_POINT_TOLERANCE_C
- 0.6.1 (2026-11-14): DQ-09 implementation fix, rule meaning unchanged: compare the difference rounded to 0.1 °C (floating-point error quarantined values exactly at temperature + 0.1 °C: Reykjavik 1988, Stockholm 1999). Only the two affected city-years were reprocessed; all other silver rows are unaffected by this fix
- 0.7.0 (2026-11-26): silver table guarantees as Delta CHECK constraints (section 3b): DQ-06...09 enforced on the table, pluse key not-null and wet-bulb plausibility (±1 °C, Stull 2011 published error). Source rules (section 2) unchanged
