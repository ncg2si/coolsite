# CoolSite – data model

Draft created 2026-11-13 (to be completed by Cami). Covers the guide's "Data modelling" requirement: purpose, grain, keys and relationships of every table. Field rules and quality checks: see `data_contract.md` (v0.5).

## 1. Overview

```
Open-Meteo API (ERA5-Land)
        │  ingest.py
        ▼
bronze  (raw JSON, 1 file per city × year)
        │  validate.py  (DQ-01..09, error budget)
        ├──────────────► quarantine  (rejected hours + rule IDs)
        ▼  transform.py
silver  (1 row per city × hour, + wet-bulb, lineage)
        │  classify.py + aggregate.py
        ▼
gold: cooling_modes  (1 row per city × year × design × mode)
        │
        ▼
dashboard (Streamlit, planned)

cities (reference table, planned: data/seed/cities.csv) ── joins on `city` with silver and gold
```

## 2. Tables

| Table | Grain (one row =) | Key | Stored as / partitioned by | Purpose |
|---|---|---|---|---|
| bronze | one **file** = one city × one load period (backfill: one calendar year) | city + start date | JSON, `data/bronze/city=<city>/<start>.json` | raw API response, never changed → can always reprocess |
| silver | one **hour** of one city | city + time | Parquet, `data/silver/`, partitioned by `city`, `year` | validated, clean hours + derived wet-bulb + lineage |
| quarantine | one **rejected row** (raw hour) | city + time — *not unique*: conflicting duplicates keep all copies | Parquet, `data/quarantine/`, partitioned by `city`, `year` | rejected hours with the rule IDs they broke, never deleted silently |
| gold `cooling_modes` | one **city × year × design × mode** | city + year + design + mode | Parquet, `data/gold/cooling_modes/`, one file (small table) | hours and share of each cooling mode → dashboard |
| cities *(planned)* | one **city** | city | CSV seed, `data/seed/cities.csv` | lat/lon, timezone, group (FLAP-D / challenger), regulatory zone, water stress |

## 3. Relationships

- bronze → silver: one bronze file produces the silver rows of one city-year partition (via `validate` + `transform`). Hours that fail a rule go to quarantine instead.
- silver → gold: gold is fully recomputed from all of silver (classify per design, then count per city × year × design × mode).
- silver / gold → cities: many-to-one on `city` (planned; used for map coordinates, timezone for hour-of-day views, water stress).
- Every valid hour belongs to exactly one cooling mode per design → per city × year × design, `sum(hours) = total_hours` (= valid hours).

## 4. Columns

### silver
| Column | Type | Unit | Meaning |
|---|---|---|---|
| city | string | — | city name, lowercase (partition column) |
| year | int | — | calendar year of `time`, UTC (partition column) |
| time | timestamp | UTC | start of the hour |
| temperature_c | double | °C | air temperature 2 m |
| humidity_pct | int | % | relative humidity 2 m |
| dew_point_c | double | °C | dew point 2 m |
| wet_bulb_c | double | °C | wet-bulb temperature, Stull (2011), computed in silver |
| source_model | string | — | weather model, `era5_land` |
| contract_version | string | — | data contract version used to validate the row |
| processed_at | timestamp | UTC | when the row was written to silver |
| run_id | string | — | id of the pipeline run that wrote the row (also in the log) |

### quarantine
| Column | Type | Meaning |
|---|---|---|
| city, time, temperature_c, humidity_pct, dew_point_c | as silver | the rejected hour as read from bronze |
| failed_rules | array<string> | IDs of the broken rules, e.g. `["DQ-07"]`, `["DQ-04"]` |
| year | int | partition column |

### gold `cooling_modes`
| Column | Type | Meaning |
|---|---|---|
| city | string | city |
| year | int | calendar year |
| design | string | `direct` or `indirect` |
| mode | string | `free`, `evaporative`, `hybrid`, `chiller` |
| hours | long | number of valid hours in this mode |
| total_hours | long | valid hours of the city-year (same for all modes of one design) |
| mode_share | double | hours ÷ total_hours (not rounded) |
| params | string | JSON of the classification parameters used (A, dew limits, ε, T_return, evap_assist) |
| processed_at | timestamp | when gold was written |

## 5. Design decisions (short)
- Time stored in UTC; local time only for hour-of-day views (timezone from `cities.csv`).
- Silver idempotent per city-year: dynamic partition overwrite (MVP); Delta MERGE on city + time planned for incremental loads.
- Gold small → one file (`coalesce(1)`), fully recomputed.
- Classification logic in one module (`classify.py`); parameters stored with gold for reproducibility.

## 6. Open / to do (Cami)
- [ ] coverage per city-year (valid ÷ expected hours, `incomplete` flag if < 99.9 %) — not yet in gold
- [ ] zero-hour modes (e.g. no `hybrid` row for Barcelona direct) — needed as 0 for the scatter
- [ ] degree-hours columns (`water_degree_hours`, `chiller_degree_hours`) — plan §3d
- [ ] cities table: columns final, source for coordinates
- [ ] diagram as image for the README / presentation
