# Data source assessment: ERA5 vs Meteostat vs ECA&D

Researched 2026-11-12 from the providers' own documentation. "Not verified" = could not be confirmed from a primary source yet.

## Decision
- **Main source: ERA5 via the Open-Meteo Historical Weather API.** The only candidate that is hourly, gap-free, covers every city since 1961 and uses one method everywhere, so cities can be compared fairly.
- **Cross-check: Meteostat** (station observations) for 2–3 cities, to measure how far ERA5 is from real measurements.
- **Rejected: ECA&D.** Daily series only; the cooling-mode classification needs hours. No dew point.

## Finding to act on: pin the model
The Open-Meteo historical API defaults to "Best match", which "combines IFS HRES, ERA5 and ERA5-Land seamlessly". `fetch_weather` sets no model, so the current data is probably not pure ERA5. IFS exists only from 2017 (9 km), so the source changes over time, which affects the 1961–1990 vs today comparison. To do: set the `models` parameter explicitly (check the exact value in the docs), reload, and name the model in the data contract.

## Comparison

| Criterion | ERA5 (via Open-Meteo) | Meteostat | ECA&D |
|---|---|---|---|
| Hourly? | Yes | Yes | No, daily series only |
| Temperature, humidity, dew point? | Yes, all three | Temperature and relative humidity confirmed; dew point not verified | Daily relative humidity and min/mean/max temperature; no dew point |
| Since when? (need 1961) | ERA5 from 1940; ERA5-Land from 1950 | Depends on the station; Frankfurt Airport hourly from 1926 | Depends on the station; not verified |
| Covers all 23 cities? | Yes, global grid (0.25°, about 25 km) | Not verified per city | Not verified per city |
| Gaps? | None (model output) | Yes; bulk files fill gaps with model data, marked in `_source` columns | Not verified |
| Same method everywhere? | Yes, if one model is pinned | No: different stations, instruments, providers | No: series from many providers |
| Licence | CC BY 4.0 with attribution; free API tier for non-commercial use only | CC BY 4.0, commercial use allowed; credit Meteostat and the original provider | Non-commercial research and education only; citation required |
| Access | JSON API; 10,000 weighted calls per day (free tier) | Bulk files per station and year (CSV / Parquet), Python library, JSON API | ASCII file downloads; no API mentioned |

## Cross-check plan (week 2)
- Stations: Frankfurt Airport `10637` (hourly inventory from 1926, verified); Helsinki-Vantaa `02974` and Madrid-Barajas `08221` (IDs and hourly inventory **not verified** — check `inventory.hourly` in Meteostat's station metadata first).
- Use observations only: filter on the `_source` columns, otherwise model data is compared with model data.
- One recent year. Compare hourly temperature and dew point (mean difference), and above all the shares of free cooling / evaporative / chiller.

## Other sources considered (not used in the MVP)
- **Copernicus Climate Data Store (CDS):** the original source of ERA5. No middleman, but NetCDF/GRIB files, a request queue and an account. Fallback if Open-Meteo's limits or terms become a problem.
- **NOAA Integrated Surface Database (ISD):** global hourly station observations; one of the kinds of source Meteostat aggregates. Rawer and harder to parse.
- **DWD open data (also via the Bright Sky API):** hourly station data, Germany only. Would cover Frankfurt and Berlin, not the other cities.
- **CERRA (via Open-Meteo):** European reanalysis at 5 km, but only 1985 to June 2021. Too short for the 1961 baseline.

## Sources
- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo licence: https://open-meteo.com/en/licence · terms: https://open-meteo.com/en/terms
- Meteostat licence: https://dev.meteostat.net/license
- Meteostat hourly bulk data: https://dev.meteostat.net/data/bulk/hourly
- Meteostat station metadata: https://dev.meteostat.net/api/stations/meta
- ECA&D daily data: https://www.ecad.eu/dailydata/index.php
- ECA&D elements: https://www.ecad.eu/dailydata/datadictionaryelement.php
- ECA&D data policy: https://www.ecad.eu/documents/ECAD_datapolicy.pdf
