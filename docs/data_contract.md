# Data contract: Open-Meteo Historical Weather → CoolSite bronze

| | |
|---|---|
| Version | 0.5 (2026-11-13) |
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
| DQ-09 | dew point ≤ temperature  + 0 °C tolerance | row | quarantine the row |

- DQ-08 provisional; refine after profiling extremes (Helsinki January, Athens July)
- DQ-09 Equality occurs only at 100 % humidity (saturation); no case of dew point > temperature in 2,640 profiled hours.
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
