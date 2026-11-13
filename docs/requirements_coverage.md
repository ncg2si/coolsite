# Requirements coverage — "Data Engineering Capstone Project Guide.pdf" (received 2026-11-05)

Status legend: ✅ done · 🟡 started · ⬜ open · ➕ optional extension

## Minimum requirements (section 8 of the guide)

Last reviewed 2026-11-13. Priority: these come before every optional extension (incl. the advanced dashboard parts). Weekly order: `dashboard_and_gold_plan.md` §5.

| Capability | Expected evidence | CoolSite status | Where / next step |
|---|---|---|---|
| Problem definition | problem, end user, objective | ✅ | docs/capstone_idea.md, CoolSite_capstone_idea.pdf |
| Data suitability | assess ≥ 2 candidate datasets, hero + fallback | ✅ | docs/second_source_assessment.md (Open-Meteo hero, Meteostat cross-check, ECA&D rejected) → add the ERA5-Land model choice (2026-11-12) |
| Data catalog | source, fields, structure, keys, relationships, limitations, update freq, governance | 🟡 | data_contract.md has fields + DQ → add: row = 1 city × 1 hour, key `city + time`, units, ~5-day delay, history since 1950 (ERA5-Land), licence |
| Architecture | diagram + justification of key decisions | ⬜ | docs/architecture.md (empty) + rewrite ADR-001 (Parquet/Delta locally → Azure Databricks) — week 3 |
| Data modelling | table purposes, grain, relationships | ⬜ | decisions exist (2026-11-12/13), write them down — week 1: bronze = 1 JSON per city × year · silver = city × hour (+ wet-bulb, year, lineage), partitioned city/year · quarantine = rejected rows + failed_rules · gold = city × year (× design) × mode · cities.csv = reference table (lat/lon, timezone, water stress) |
| Ingestion and storage | reproducible pipeline, storage strategy, raw data preserved | 🟡 | ingest.py: model pinned (era5_land) ✅, bronze raw JSON ✅ · loop per city × year, skip-if-exists, throttling, run metadata ⬜ — week 2 |
| Incremental processing | new/changed data, updated records, no duplicates, recover partway, watermark | ⬜ | watermark per city + 7-day lookback (ERA5T revisions = updated records) + Delta MERGE on city + time; advance watermark only after success — weeks 2–3 |
| Logging | start/finish, stage, counts extracted/processed/rejected/written, status, error | ⬜ | still print() → src/utils/logging.py, used in ingest / validate / transform — week 1 |
| Data quality | meaningful checks + tests | ✅ | validate.py DQ-01..09 + error budget, tests/test_validate.py (incl. broken files); test_wetbulb.py in progress |
| Error handling | failure handling + recovery, DEMONSTRATED failure scenario, quarantine invalid records, retries | 🟡 | schema gate ✅ · quarantine ✅ · error budget ✅ · retries in ingest ⬜ · failure demo + recovery ⬜ — weeks 2–3 |
| Version control | Git + setup/run instructions | 🟡 | Git ✅ · README with setup + run steps ⬜ — week 4 |
| Governance and security | usage, privacy, access, credentials | ⬜ | one page: Open-Meteo + ERA5-Land/Copernicus licence and attribution; no personal data; no API key needed; .env never committed — week 2 |
| Data product | curated dataset / analytical output for the use case | ⬜ | gold tables (documented) + dashboard core — week 4 |
| Documentation | setup, run, understand (11 sections, guide §10) | ⬜ | README + docs/ — week 4 |
| Demonstration | working solution you can explain | ⬜ | final presentation + failure demo |

## Optional extensions (section 9) relevant to CoolSite

| Extension | Plan |
|---|---|
| ➕ Cloud deployment | Azure Databricks (planned upgrade, capstone week 3) |
| ➕ Distributed processing | PySpark / Spark SQL (already used locally) |
| ➕ dbt | optional |
| ➕ CI/CD | GitHub Actions running pytest (optional) |
| ➕ Advanced orchestration | Airflow locally / Databricks Workflows |
| ➕ Dashboard | core (map, scatter, bars, heatmap, direct/indirect switch) firm in week 4 because it carries the presentation; advanced parts (threshold sliders via histogram, click drill-down, water stress stage 2) only after all minimum requirements |

## Documentation sections required (guide §10)
1 overview · 2 dataset assessment · 3 data catalog · 4 governance · 5 architecture · 6 data model ·
7 pipeline implementation · 8 incremental processing · 9 reliability · 10 results · 11 future improvements
