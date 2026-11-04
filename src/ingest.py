import json
from pathlib import Path
import requests

URL = "https://archive-api.open-meteo.com/v1/archive"
ROOT = Path(__file__).resolve().parents[1]
BRONZE = ROOT / "data" / "bronze"

def fetch_weather(lat: float, lon: float, start: str, end: str) -> dict:
    """Call Open-Meteo and return the raw JSON response as a dict."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m",
    }
    response = requests.get(url=URL, params=params, timeout=5)
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
    data = fetch_weather(50.11, 8.68, "2026-06-01", "2026-09-01")
    path = save_bronze(data, "frankfurt", "2026-06-01")
    print("saved:", path)