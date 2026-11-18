import json
from pathlib import Path
import requests
import pandas as pd
import time
from datetime import datetime, timezone, date

from contract import WEATHER_MODEL
from paths import BRONZE, CITIES_FILE

from utils.log import get_logger

CALLS_PER_CITY_YEAR = 365 / 14 * 3 / 10    # ≈ 7.8 weighted calls (3 variables, 1 year)
DAILY_BUDGET = 9000                       # below the 10,000/day free limit, with a safety margin


RETRY_WAITS = [10, 30, 60]
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
class QuotaExhausted(Exception):
    """Daily or monthly API limit reached; Retrying today is pointless"""

log = get_logger(Path(__file__).stem)

URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_weather(lat: float, lon: float, start: str, end: str) -> dict:
    """Call Open-Meteo and return the raw JSON response as a dict."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m",
        "models": WEATHER_MODEL,
        "timezone": "GMT",
    }
    last_error = None
    for attempt, wait in enumerate([0] + RETRY_WAITS):
        if wait:
            log.warning(f"retry {attempt}/{len(RETRY_WAITS)} in {wait} s ({last_error}) ")
            time.sleep(wait)
        try:
            response = requests.get(url=URL, params=params, timeout=60)
            if response.status_code == 429:
                try:
                    reason = response.json().get("reason","")
                except ValueError: 
                    reason = ""
                if "Daily" in reason or "Monthly" in reason:
                    raise QuotaExhausted(reason) #not an HTTP error -> not caught below
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code not in RETRYABLE_STATUS:
                raise # e.g. 400 Bad request -> retrying is pointless
            last_error = e
        except (requests.ConnectionError, requests.Timeout) as e: 
            last_error = e
    raise last_error #all 4 attempts failed

    

def new_bronze_path(city: str, start: str, end: str, fetched_at: datetime):
    stamp = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    return BRONZE / f"city={city.lower()}" / f"{start}_{end}__fetched_{stamp}.json"


def latest_bronze_path(city: str,start: str,end: str) -> Path:
    "Newest bronze file for this time window, or None"
    files = sorted ((BRONZE / f"city={city.lower()}").glob(f"{start}_{end}__fetched_*.json"))
    if not files:
        return None
    return files[-1]


def save_bronze(data: dict, city: str, start: str, end: str) -> Path:
    """Save the raw response unchanged to the bronze layer."""
    fetched_at = datetime.now(timezone.utc)
    file_path = new_bronze_path(city, start, end, fetched_at)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data,indent=2))
    return file_path

def load_cities(path=CITIES_FILE):
    cities = pd.read_csv(path)
    return cities[cities["active"] == True]

def api_cost(start: str, end: str, n_vars: int = 3) -> float:
    """Weighted Open-Meteo calls: days/14 x variables/10, at least 1."""
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    return max(1.0, days / 14 * n_vars / 10)


def ingest_window(city:str, lat: float, lon: float, start: str, end:str) -> str:
    """Fetch one window into a NEW bronze file. Skip if a file for this window exists."""
    if latest_bronze_path(city,start,end) is not None:
        log.info(f"{city} {start}..{end}: already in bronze -> skipped")
        return "skipped"
    data = fetch_weather(lat,lon,start,end)
    save_bronze(data,city,start,end)
    #time.sleep(1) # be polite: at most ~1 request per second
    # limit 5000 calls/hour -> with 7.8 calls/file we get 640 files/hour.  The sleep time between calls should be 3600/640 = 5.6s/file 
    time.sleep(6)
    log.info(f"{city} {start}..{end} loaded")
    return "loaded"


def ingest_city_year(city: str,lat: float,lon: float,year: str):
    return ingest_window(city,lat,lon, f"{year}-01-01",f"{year}-12-31")

if __name__ == "__main__":
    # data = fetch_weather(50.11, 8.68, "2025-01-01", "2025-12-31")
    # path = save_bronze(data, "frankfurt", "2025-01-01")
    #data = fetch_weather(41.3888, 2.159, "2025-01-01", "2025-12-31")
    #path = save_bronze(data, "barcelona", "2025-01-01")
    #print("saved:", path)
    #print(load_cities())
    cities = load_cities().head(3)
    years = [2024, 2025]

    for row in cities.itertuples():
        for year in years:
            ingest_city_year(row.city,row.lat,row.lon, year)
        