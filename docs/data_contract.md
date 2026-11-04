# Data contract: Open-Meteo Historical Weather → CoolSite bronze

| | |
|---|---|
| Version | 0.1 (2026-11-04) |
| Producer | Open-Meteo Historical Weather API (ERA5 reanalysis) |
| Consumer | CoolSite pipeline (transform → silver) |
| Owner | Cam Lai Ngo |
| Profiled with | notebooks/01_explore_api.ipynb: Frankfurt, 2026-06-01 → 2026-09-01 |

## 1. Schema
- Endpoint: https://archive-api.open-meteo.com/v1/archive
- Storage: data/bronze/city=<city lowercase>/<start>.json, raw response, unchanged
- Structure: metadata on top (latitude, longitude, timezone, elevation);
  hourly values in data["hourly"] as equal-length lists (one list = one column)
- Grain: one row per city × hour

| field | type in bronze | type in silver | unit | meaning |
|---|---|---|---|---|
| time | ISO text | datetime, UTC | — | start of the hour |
| temperature_2m | float | float | °C | air temperature 2m above ground |
| dew_point_2m | float | float | °C | dew point 2m above ground |
| relative_humidity_2m | int | int | % | relative humidity 2m above ground |

## 2. Quality rules (implemented in src/validate.py)
| ID | Rule | Severity |
|---|---|---|
| DQ-01 | rows = days × 24 (both dates inclusive) | error |
| DQ-02 | no nulls in any field | error |
| DQ-03 | no duplicate hours | error |
| DQ-04 | hourly steps of exactly 1 h, increasing | error |
| DQ-05 | humidity 0–100 % | error |
| DQ-06 | temperature -50 to 55 °C | error |
| DQ-07 | dew point ≤ temperature  + 0 °C tolerance | error |
| DQ-08 | timezone = "GMT" | error |
| DQ-09 | all expected fields present (schema drift check) | error |

- DQ-06 provisional; refine after profiling extremes (Helsinki January, Athens July)
- DQ-07 Equality occurs only at 100 % humidity (saturation); no case of dew point > temperature in 2,640 profiled hours.

## 3. Freshness
- ERA5 arrives with ~5 days delay; the most recent days come from another model
  and may be revised → every run reloads the last 7 days (overwrite, idempotent)

## 4. Change handling
- New field in the response → log a warning. A new field doesn't harm the pipeline but an expected field missing or renamed does. 
- Expected field missing or renamed → DQ-09 fails → pipeline stops, bronze is kept
- Contract change → raise the version number, note it here

## 5. Change log
- 0.1 (2026-11-04): first version, from profiling Frankfurt (summer sample only)