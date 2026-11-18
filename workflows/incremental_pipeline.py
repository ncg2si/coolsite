import sys
from pathlib import Path
from datetime import date

from aggregate import build_gold
from incremental import fetch_window, split_by_year,get_watermarks
from ingest import load_cities, api_cost, ingest_window, QuotaExhausted
from paths import SILVER
from transform import transform_city_year
from utils.log import get_logger
from spark_utils import get_spark

log = get_logger(Path(__file__).stem)

MAX_INGEST_ERRORS_IN_A_ROW = 5      # API down or blocking → stop instead of hammering it

def silver_exists(city, year):
    return (SILVER / f"city={city}" / f"year={year}").exists()

def run_incremental(cities, today: date, daily_budget: float =5000) -> list[str]:
    """Bring every city up to today - 7 days . Backfill = a city without silver."""
    watermarks = get_watermarks(get_spark())
    calls_used, failures, errors_in_a_row = 0.0, [], 0

    for row in cities.itertuples():
        start, end = fetch_window(watermarks.get(row.city),today)
        log.info(f"{row.city}: watermark {watermarks.get(row.city)} -> window {start}..{end} ")
        for c_start, c_end in split_by_year(start,end):
            s, e = c_start.isoformat(), c_end.isoformat()
            cost = api_cost(s,e)
            if calls_used + cost > daily_budget:
                log.info(f"daily budget ({daily_budget}) reached ({calls_used:.0f}) calls -> stop")
                build_gold()
                return failures
            #1 bronze
            try:
                status = ingest_window(row.city,row.lat,row.lon,s,e)
                errors_in_a_row = 0
            except QuotaExhausted as err:
                log.error(f"API quote exhausted ({err}) -> stop, run again tomorrow")
                build_gold()
                return failures
            except Exception:
                log.exception(f"{row.city} {s}..{e}: ingest FAILED -> skipped")
                failures.append(f"{row.city} {s}..{e} (ingest)")
                errors_in_a_row += 1
                if errors_in_a_row >= MAX_INGEST_ERRORS_IN_A_ROW:
                    log.error("too many ingest errors in a row -> stop")
                    build_gold()
                    return failures
                continue
            if status == "loaded":
                calls_used += cost
            #2 silver (new bronze, or silver partition missing)

            if status == "loaded" or not silver_exists(row.city, c_start.year):
                try:
                    transform_city_year(row.city, s, e)
                except Exception:
                    failures.append(f"{row.city} {s}..{e} (transform)")
    
    log.info(f"incremental run finished: {calls_used:.0f} API calls used")
    build_gold()
    return failures


if __name__ == "__main__":
    cities = load_cities()
    #cities = cities[cities["city"] == "berlin"]       # TEST: one city first
    failures = run_incremental(cities, today=date.today())
    if failures:
        log.error(f"{len(failures)} window(s) failed: {', '.join(failures)}")
        sys.exit(1)
    log.info("incremental run OK")          