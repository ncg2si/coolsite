import pandas as pd
import requests

from koppen import koppen_at, load_legend
from paths import CITIES_ALL_FILE, CITIES_LIST_ALL, KOPPEN_TIF

LEGEND = load_legend()
URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode(name, country, admin1=None):
    params = {
        "name": name,
        "count": 10,  # changed from 1 to 10 candidates with same names
        "format": "json",
        "language": "en",
        "countryCode": country,
    }
    response = requests.get(URL, params, timeout=30)
    response.raise_for_status()
    results = response.json()["results"]
    if pd.isna(admin1):  # emtpy cell in csv is NaN
        result = results[0]
    else:
        result = next((r for r in results if r.get("admin1") == admin1), None)
        if result is None:
            raise ValueError(
                f"{name} : no result in {admin1}, got {[r.get('admin1') for r in results]}"
            )

    return (
        result["latitude"],
        result["longitude"],
        result["timezone"],
        result.get("country", country),
        result.get("admin1"),
    )


def climate(lat, lon):
    zone = koppen_at(KOPPEN_TIF, lat, lon, LEGEND)
    if zone:
        return zone["class"], zone["description"]
    else:
        return None, None


def build(input_path, output_path):

    cities = pd.read_csv(input_path)
    columns = ["lat", "lon", "timezone", "country_name", "admin1_found"]
    cities[columns] = cities.apply(
        lambda row: geocode(row["name"], row["country"], row["admin1"]),
        axis=1,
        result_type="expand",
    )
    cities["lat"] = cities["lat"].round(2)
    cities["lon"] = cities["lon"].round(2)
    cities[["climate_class", "climate_description"]] = cities.apply(
        lambda row: climate(row["lat"], row["lon"]), axis=1, result_type="expand"
    )
    cities.to_csv(output_path, index=False)


if __name__ == "__main__":
    # build(CITY_LIST_FILE,CITIES_FILE)
    # build(CITY_LIST_GLOBAL_FILE,CITIES_GLOBAL_FILE)
    build(CITIES_LIST_ALL, CITIES_ALL_FILE)
