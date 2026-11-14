import json
from pathlib import Path
import requests
import pandas as pd
import time

from contract import WEATHER_MODEL
from paths import BRONZE, CITIES_FILE

from utils.log import get_logger

CALLS_PER_CITY_YEAR = 365 / 14 * 3 / 10    # ≈ 7.8 weighted calls (3 variables, 1 year)
DAILY_BUDGET = 9000                       # below the 10,000/day free limit, with a safety margin


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
    response = requests.get(url=URL, params=params, timeout=60)
    response.raise_for_status()
    return response.json()

def bronze_path(city: str, start: str) -> Path:
    """The path to bronze file"""
    return BRONZE / f"city={city.lower()}" / f"{start}.json"    

def save_bronze(data: dict, city: str, start: str) -> Path:
    """Save the raw response unchanged to the bronze layer."""
    file_path = bronze_path(city, start)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data,indent=2))
    return file_path


def load_cities():
    cities = pd.read_csv(CITIES_FILE)
    return cities[cities["active"] == True]


def ingest_city_year(city,lat,lon,year):
    start, end = f"{year}-01-01", f"{year}-12-31"
    path = bronze_path(city,start)
    if path.exists():
        log.info(f"{city} {year}: already in bronze -> skipped")
        return "skipped"
    data = fetch_weather(lat,lon,start,end)
    save_bronze(data,city,start)
    time.sleep(1) # be polite: at most ~1 request per second
    log.info(f"{city} {year} loaded")
    return "loaded"

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
        