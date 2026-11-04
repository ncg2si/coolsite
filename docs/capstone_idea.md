# CoolSite – Climate suitability for data centres (FLAP-D vs challengers)

> CoolSite: free cooling, water or chillers? A climate pipeline for European data centre siting.

Status: business requirements DRAFT v3 — not yet reviewed by instructors (Gate 1)
Last updated: 2026-11-02 (problem statement)

## 0. Problem statement (my words)

Companies planning new data centres look beyond the FLAP-D markets (Frankfurt, London, Amsterdam, Paris, Dublin) because those markets are short of grid capacity and land. Cooling is the largest energy overhead of a data centre, and the climate decides how a site is cooled:

- cool air → free air cooling (fans only: low electricity, no water)
- hot and dry → evaporative cooling (low electricity, high water use)
- hot and humid (high wet-bulb) → chillers (high electricity use)

Germany's Energy Efficiency Act (EnEfG) sets a PUE target of 1.2 for new data centres. The EU data centre rating grades PUE (electricity) and WUE (water) separately, and it does not adjust those grades for climate. A site-selection team therefore needs a climate answer: does this city's climate push a new data centre toward high electricity use, high water use, or neither?

The comparison is 18 challenger cities against the five FLAP-D cities, for Europe (EU plus selected non-EU benchmark cities), per city and per year. The questions it must answer are: "Which cities save electricity without becoming water-dependent?" and "How has this balance changed from 1961–1990 to today?"

## Decisions so far

- Path A (domain-driven)
- User: company deciding where to build a data centre (one user only; ops team / live alerts = optional stretch goal)
- Scope: 5 FLAP-D cities (baseline) + 10 challenger cities (Nordic, southern, central/east)
- Non-EU cities allowed for climate comparison; every city gets a `regulatory_zone` flag (EU / EEA / non-EU). Baseline already contains London (non-EU).
- City scope (2026-10-19): keep the full candidate list (18 challengers, see candidate_cities.md) + 5 FLAP-D = 23 cities; no narrowing for now. Open: one inclusion rule instead of 23 individual reasons; develop with 3 cities first (Frankfurt + 1 cold + 1 hot), scale via cities.csv. Problem statement updated 2026-11-02 to 18 challengers.
- Reference city: Frankfurt (reason to write down: German EnEfG applies there)
- Metrics:
  - Free-cooling hours per year (dry-bulb below threshold) → efficiency / PUE, whole year
  - Hours above wet-bulb threshold → resilience / outage risk, extremes
  - Candidate: heating degree days → ERF / waste-heat reuse (same temperature data)
- Thresholds are config/seed data, not hard-coded (source: ASHRAE recommended range — to verify)
- Wet-bulb: take Open-Meteo value AND compute own (Stull 2011) → unit test comparing both
- Extra #1 (decided 2026-10-20): climate projections to 2050 via Open-Meteo Climate API (CMIP6 HighResMIP, 7 models, downscaled 10 km, DAILY only, 1950–2050, ~RCP8.5; attribution to CMIP6 + Open-Meteo required). Built only after the core pipeline runs. Open: daily proxy metric for free-cooling hours (e.g. days with Tmax < X °C), validated against hourly history where both exist; show model range (band), not one number; which models; projection years.
- DECIDED (2026-10-31): cooling-mode classification is the CORE of the project. Key dashboard question: "Does this city's climate push a data centre towards high electricity use (chiller → worse PUE), high water use (evaporative → WUE pressure), or neither (free cooling → good PUE and WUE)?" Details: classify every hour into exactly one cooling mode with 2 thresholds — mode 1 free cooling (T < A, optionally dew point ≤ 15 °C per ASHRAE), mode 2 evaporative/water (T ≥ A and wet-bulb ≤ B), mode 3 chiller (wet-bulb > B). 'Water hours' (mode 2) = proxy for water use (WUE), NOT litres. DQ check: mode1+mode2+mode3 = hours in year (8760/8784). Assumption to document: mode 3 uses dry cooler (no water); with cooling towers mode 3 also uses water.
- Threshold sources so far: ASHRAE TC 9.9 (2016) Power Equipment Thermal Guidelines, Table 2 p.11–12: recommended 18–27 °C inlet, DP −9..15 °C, RH ≤ 60% (PRIMARY). Wet-bulb threshold B: no source yet → parameter.
- Climate is the core; at most 2 extra layers. Candidates: hand-maintained capacity seed CSV (MW per city, source + report date, SCD2), one hazard layer, water stress (WUE), grid renewable share (REF), station data cross-check (Meteostat/ECA&D)
- Main data source: Open-Meteo Historical Weather API (ERA5, hourly since 1940, ~5-day delay)
- Storage (ADR-001 draft): silver + gold as Parquet in S3 (OLAP workload: filter per city, aggregate). DynamoDB and RDS rejected.
- Updates: new hours = append (new partition); recent days may be corrected → reload last ~7 days and overwrite those partitions (idempotent, also = backfill mechanism). True live view = separate speed layer (DynamoDB), deferred.

- DECIDED (2026-11-04): build LOCALLY first (thin slice → full local pipeline = guaranteed, gradable fallback), then MIGRATE to Databricks (target: Azure Databricks; plan B: Databricks Free Edition). Decision rule: if the Databricks move is not working by mid capstone week 3, present the local pipeline + deployed thin slice + migration plan. Portability rules: pure logic separate from IO; all paths/settings in config (local.yaml vs azure.yaml); Delta format from day one if possible; transforms in Spark SQL/PySpark (not pandas-specific); secrets only via env vars. Open: local setup option A (Docker+Airflow+Postgres+pandas) vs B (Airflow + Delta + PySpark or DuckDB) — decide before step 2 (first transform). Databricks learning: 4 sessions on Free Edition before capstone start.

## Out of scope
Fibre, permits, community, electricity prices, land; per-facility PUE/WUE/ERF/REF (confidential under EU 2024/1364).

## Open items

- [ ] 1. City list: 10 challengers, one-line reason each, lat/lon, regulatory_zone → seed CSV `city, country, region, group, regulatory_zone, lat, lon, reason` (mix ~3 cold / 4 hot / 3 in between; Madrid + Milan together for humid-vs-dry test)
- [ ] 1b. Verify: does EU 2024/1364 / EED apply to EEA (Norway, Iceland)?
- [ ] 2. Metric definitions: exact thresholds + source; time window (e.g. 1991–2020 vs last 5 years)
- [ ] 2b. Define or drop "climate PUE potential"; decide on heating degree days
- [ ] 3. Freshness: backfill from 1961-01-01 (decided 2026-10-20; reason still to write in my words — two WMO reference periods 1961–1990 vs 1991–2020 + recent years), daily refresh
- [ ] 4. Output: dashboard + gold table; example questions; filter by regulatory zone
- [ ] 5. Extras (max 2) with user-side reason
- [ ] 7. Data sources + licences
- [ ] 8. Success criteria
- [ ] ADR-001 blanks (see docs/adr/ADR-001-storage.md)
- [ ] Data exercise: correlation between free-cooling hours and wet-bulb hours across the 15 cities

## Sources
- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- EU Delegated Regulation 2024/1364: https://eur-lex.europa.eu/eli/reg_del/2024/1364/oj/eng
- EnEfG summary (CMS): https://cms.law/de/deu/publication/2026-themen-die-sie-bewegen-werden/klimaneutrale-rechenzentren-testfall-fuer-die-industrie
- FLAP-D / next hotspots (Soben, Nov 2024): https://sobencc.com/insights/forget-flapd-here-are-the-next-data-centre-hotspots-soben/
- EU renewables for DCs (Jones Day, Jun 2026): https://www.jonesday.com/en/insights/2026/06/green-data-centers-pioneering-energy-efficiency-and-sustainability-in-the-eu
