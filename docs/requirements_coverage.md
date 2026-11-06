# Requirements coverage — "Data Engineering Capstone Project Guide.pdf" (received 2026-11-05)

Status legend: ✅ done · 🟡 started · ⬜ open · ➕ optional extension

## Minimum requirements (section 8 of the guide)

| Capability | Expected evidence | CoolSite status | Where / next step |
|---|---|---|---|
| Problem definition | problem, end user, objective | ✅ | docs/capstone_idea.md §0 |
| Data suitability | assess ≥ 2 candidate datasets, hero + fallback | ⬜ | only Open-Meteo so far → add a fallback (e.g. ERA5 via Copernicus CDS, Meteostat stations) |
| Data catalog | source, fields, structure, keys, relationships, limitations, update freq, governance | 🟡 | docs/data_contract.md covers fields + DQ → extend to a catalog (keys, update frequency, licence) |
| Architecture | diagram + justification of key decisions | ⬜ | docs/architecture.md (empty) + ADRs |
| Data modelling | table purposes, grain, relationships | ⬜ | bronze / silver / gold grain; star schema vs OBT decision |
| Ingestion and storage | reproducible pipeline, storage strategy, raw data preserved | 🟡 | src/ingest.py ✅ (bronze = raw, overwrite = idempotent); run metadata missing |
| Incremental processing | new/changed data, updated records, no duplicates, recover partway, watermark | ⬜ | ERA5 revisions = "records updated after ingestion" → reload last 7 days + watermark per city |
| Logging | start/finish, stage, counts extracted/processed/rejected/written, status, error | ⬜ | src/utils/logging.py |
| Data quality | meaningful checks + tests | 🟡 | src/validate.py: structural DQ-01/08/09 ✅, content DQ-02..07 (Spark) next; pytest |
| Error handling | failure handling + recovery, DEMONSTRATED failure scenario, quarantine invalid records, retries | 🟡 | schema gate ✅ · quarantine table for bad rows ⬜ · retries in ingest ⬜ · failure demo ⬜ |
| Version control | Git + setup/run instructions | ⬜ | git init + commits (GitHub optional) · README |
| Governance and security | usage, privacy, access, credentials | ⬜ | Open-Meteo licence/attribution; no personal data; no secrets needed for Open-Meteo |
| Data product | curated dataset / analytical output for the use case | ⬜ | gold: cooling-mode hours per city × year (dashboard optional) |
| Documentation | setup, run, understand (11 sections, guide §10) | ⬜ | README + docs/ |
| Demonstration | working solution you can explain | ⬜ | final presentation |

## Optional extensions (section 9) relevant to CoolSite

| Extension | Plan |
|---|---|
| ➕ Cloud deployment | Azure Databricks (planned upgrade, capstone week 3) |
| ➕ Distributed processing | PySpark / Spark SQL (already used locally) |
| ➕ dbt | optional |
| ➕ CI/CD | GitHub Actions running pytest (optional) |
| ➕ Advanced orchestration | Airflow locally / Databricks Workflows |
| ➕ Dashboard | optional — analytical tables are enough |

## Documentation sections required (guide §10)
1 overview · 2 dataset assessment · 3 data catalog · 4 governance · 5 architecture · 6 data model ·
7 pipeline implementation · 8 incremental processing · 9 reliability · 10 results · 11 future improvements
