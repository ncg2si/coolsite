from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]   # src/paths.py → parents[0] = src, parents[1] = coolsite


DATA = Path(os.environ.get("COOLSITE_DATA", PROJECT_ROOT / "data")) # if no env var COOLSITE_DATA use data as the directory


BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
QUARANTINE = DATA / "quarantine"
GOLD = DATA / "gold" / "cooling_modes"
LOGS = PROJECT_ROOT / "logs"
STAGING = DATA / "staging"

# climate classification
KOPPEN_DIR = DATA / "reference" / "koppen" / "koppen_geiger_tif"
LEGEND_FILE = KOPPEN_DIR/ "legend.txt"
KOPPEN_TIF = KOPPEN_DIR / "1991_2020" / "koppen_geiger_0p1.tif"

# seed
#FLAP-D plus challenger cities -> Group 1
CITIES_FILE = DATA / "seed" / "cities.csv" 
CITY_LIST_FILE = DATA / "seed" / "city_list.csv"

#global without group 1 
CITIES_GLOBAL_FILE = DATA / "seed" / "cities_global.csv"
CITY_LIST_GLOBAL_FILE = DATA / "seed" / "city_list_global.csv"

#all cities from 2026 report, categorized in tiers 1-2-3 
CITIES_ALL_FILE = DATA / "seed" / "cities_all.csv"
CITIES_LIST_ALL = DATA / "seed" / "city_list_all.csv"