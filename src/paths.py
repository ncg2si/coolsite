from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]   # src/paths.py → parents[0] = src, parents[1] = coolsite

DATA = PROJECT_ROOT / "data"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
QUARANTINE = DATA / "quarantine"
GOLD = DATA / "gold" / "cooling_modes"
LOGS = PROJECT_ROOT / "logs"

# climate classification
KOPPEN_DIR = DATA / "reference" / "koppen" / "koppen_geiger_tif"
LEGEND_FILE = KOPPEN_DIR/ "legend.txt"
KOPPEN_TIF = KOPPEN_DIR / "1991_2020" / "koppen_geiger_0p1.tif"

# seed
CITIES_FILE = DATA / "seed" / "cities.csv"
CITY_LIST_FILE = DATA / "seed" / "city_list.csv"

CITY_LIST_GLOBAL_FILE = DATA / "seed" / "city_list_global.csv"
CITIES_GLOBAL_FILE = DATA / "seed" / "cities_global.csv"