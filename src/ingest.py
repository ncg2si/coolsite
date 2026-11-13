import json
from pathlib import Path
import requests

from contract import WEATHER_MODEL
from paths import BRONZE

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

if __name__ == "__main__":
    # data = fetch_weather(50.11, 8.68, "2025-01-01", "2025-12-31")
    # path = save_bronze(data, "frankfurt", "2025-01-01")
    data = fetch_weather(41.3888, 2.159, "2025-01-01", "2025-12-31")
    path = save_bronze(data, "barcelona", "2025-01-01")
    print("saved:", path)