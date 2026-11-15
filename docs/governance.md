# Governance and security



## 1. Data sources, licences and attribution

| Source | Used for | Licence | Required attribution | Primary source checked |
|---|---|---|---|---|
| Open-Meteo Historical Weather API | hourly weather (bronze) | CC BY 4.0 | "Weather data by Open-Meteo.com"  | https://open-meteo.com/en/licence (2026.11.15) |
| ERA5-Land (Copernicus Climate Change Service, ECMWF) | model behind the Open-Meteo data (`models=era5_land`) | CC-BY 4.0 | "contains modified Copernicus Climate Change Service information <2019>." | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview (2026.11.15) |
| Open-Meteo Geocoding API (based on GeoNames) | city coordinates + timezone (`build_cities.py`) | CC-BY 4.0 | Location data based on GeoNames | https://www.geonames.org |
| Beck et al. 2023, Köppen-Geiger 1991–2020, 0.1° | climate class per city | CC BY 4.0 | Beck et al. 2023, Scientific Data, doi:10.1038/s41597-023-02549-6 | https://www.nature.com/articles/s41597-023-02549-6 |
| WRI Aqueduct 4.0 (baseline monthly) | water stress per basin (planned) | CC-BY 4.0 | Kuzma et al. 2023, Aqueduct 4.0: Updated Decision-Relevant Global Water Risk Indicators| https://www.wri.org/research/aqueduct-40-updated-decision-relevant-global-water-risk-indicators?auHash=74cRjEQPsH0NDpgT1NqIfNpqV-QpYNR4oiPo1HRhpGs |
| Cushman & Wakefield, Global Data Center Market Comparison 2025 | selection of the 44 global cities (names only, no data reused) | not applicable (cited, not redistributed) | cite the report | https://assets.cushmanwakefield.com/-/media/cw/apac/vietnam/insights/2025/2025-global-data-center-market-comparison---eng.pdf |

Where attribution must appear: (README, dashboard footer, presentation last slide).

## 2. Usage restrictions
- Open-Meteo free tier: non-commercial use only; limits 600/min, 5,000/h, 10,000/day, 300,000/month ([How is one API call defined](https://open-meteo.com/en/pricing)).
- This project is a non-commercial bootcamp capstone. For commercial use, the data licences (mostly CC BY) allow reuse with attribution, but the access route must change: a paid Open-Meteo plan or direct ERA5-Land download from the Copernicus CDS. Only the ingestion module changes; validation, silver and gold stay the same. The Aqueduct licence must be verified first.
- Raw reference files (`data/reference/`) are not redistributed in the repo (`.gitignore`).

## 3. Personal data and privacy
- The pipeline processed no personal data
- City coordinates are public place names, not addresses of real data centres.

## 4. Access, credentials and secrets
- API keys needed: TODO
- `.env`, `*.pem`, Terraform state: never committed (`.gitignore`) — TODO: list what is in `.gitignore` today.
- Local storage only so far; Azure Databricks (week 3): TODO — who has access, where secrets will live (Databricks secret scope / Key Vault?).

## 5. Data retention and reproducibility
- Bronze keeps the raw API response unchanged → silver and gold can be rebuilt.
- TODO: how long is data kept? what is deleted and when (quarantine reprocessing, see decision log)?

## 6. Open questions
- TODO
