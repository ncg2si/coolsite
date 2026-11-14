from paths import CITY_LIST_FILE, CITIES_FILE,  LEGEND_FILE, KOPPEN_TIF

import requests

import pandas as pd
from koppen import load_legend, koppen_at

LEGEND = load_legend()
URL = "https://geocoding-api.open-meteo.com/v1/search"

def geocode(name,country):
    params = {
        "name":name,
        "count":1,
        "format":"json",
        "language":"en",
        "countryCode":country
    }
    response = requests.get(URL,params,timeout=30)
    response.raise_for_status()
    result = response.json()["results"][0]
    return result["latitude"], result ["longitude"], result["timezone"], result ["country"]

def climate(lat,lon):
    zone = koppen_at(KOPPEN_TIF,lat,lon,LEGEND)
    if zone:
        return zone["class"], zone["description"]
    else:
        return None,None



if __name__ == "__main__":
    cities = pd.read_csv(CITY_LIST_FILE)
    #print(geocode("frankfurt","DE"))
    columns = ["lat","lon","timezone","country_name"]
    cities[columns] = cities.apply(lambda row: geocode(row["name"],row["country"]),axis = 1, result_type= "expand")
    cities["lat"] = cities["lat"].round(2)
    cities["lon"] = cities["lon"].round(2)
    cities[["climate_class","climate_description"]] = cities.apply( lambda row: climate(row["lat"],row["lon"]),axis = 1, result_type= "expand")
   
    print(cities)
