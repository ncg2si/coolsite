import sys
from pathlib import Path

from aggregate import build_gold
from ingest import load_cities, ingest_city_year, CALLS_PER_CITY_YEAR, DAILY_BUDGET, QuotaExhausted
from paths import SILVER, CITIES_GLOBAL_FILE, CITIES_ALL_FILE
from transform import transform_city_year
from utils.log import get_logger

log = get_logger(Path(__file__).stem)

MAX_INGEST_ERRORS_IN_A_ROW = 5      # API down or blocking us → stop instead of hammering it


def silver_exists(city, year):
    return (SILVER / f"city={city}" / f"year={year}").exists()


def run_pipeline(cities, years, daily_budget = DAILY_BUDGET, ingest_only = False):
    """Ingest + transform every city × year, then build gold once.
    One failing city-year is logged and skipped; the run continues. Returns the list of failures."""
    calls_used = 0
    failures = []
    ingest_errors_in_a_row = 0

    for row in cities.itertuples():
        for year in years:
            if calls_used + CALLS_PER_CITY_YEAR > daily_budget:
                log.info(f"daily budget ({daily_budget}) reached ({calls_used:.0f} calls) -> stop, run again tomorrow")
                if not ingest_only:
                    build_gold()
                return failures

            # 1. ingest (skip if bronze exists)
            try:
                status = ingest_city_year(row.city, row.lat, row.lon, year)
                ingest_errors_in_a_row = 0
            except QuotaExhausted as err:
                log.error(f"API quota exhausted ({err}) -> stop, run again tomorrow")
                if not ingest_only:
                    build_gold()
                return failures
            except Exception:
                log.exception(f"{row.city} {year}: ingest FAILED -> skipped, continue")
                failures.append(f"{row.city} {year} (ingest)")
                ingest_errors_in_a_row += 1
                if ingest_errors_in_a_row >= MAX_INGEST_ERRORS_IN_A_ROW:
                    log.error(f"{ingest_errors_in_a_row} ingest errors in a row -> API problem? stop the run")
                    if not ingest_only:
                        build_gold()
                    return failures
                continue
            if status == "loaded":
                calls_used += CALLS_PER_CITY_YEAR

            # 2. transform (only new bronze or missing silver)
            if ingest_only:
                continue
            elif status == "loaded" or not silver_exists(row.city, year):
                try:
                    transform_city_year(row.city, f"{year}-01-01", f"{year}-12-31")
                except Exception:
                    # details are already in the log from transform_city_year
                    failures.append(f"{row.city} {year} (transform)")

    log.info(f"pipeline finished: {calls_used:.0f} API calls used")
    if not ingest_only:
        build_gold()
    return failures


if __name__ == "__main__":
    #cities = load_cities() #default Europe
    #cities = load_cities(CITIES_GLOBAL_FILE)
    cities = load_cities(CITIES_ALL_FILE) # global
    years = range(1961, 2026)           # 1961 … 2025
    failures = run_pipeline(cities, years,daily_budget= 5000, ingest_only= True)
    if failures:
        log.error(f"{len(failures)} city-year(s) failed: {', '.join(failures)}")
        sys.exit(1)                     # signal failure to whoever started the run
    log.info("all city-years OK")
