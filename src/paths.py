from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]   # src/paths.py → parents[0] = src, parents[1] = coolsite
DATA = Path(os.environ.get("COOLSITE_DATA", PROJECT_ROOT / "data")) # if no env var COOLSITE_DATA use data as the directory


# Where are we running? Databricks clusters set this variable:
ON_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ
# Unity catalog name (override with an env var if the workspace is recreated)
CATALOG = os.environ.get("COOLSITE_CATALOG","dbw_coolsite_7405619082079658")

if ON_DATABRICKS:
    BRONZE = Path(f"/Volumes/{CATALOG}/bronze/raw_files")
    SEED_DIR = Path(f"/Volumes/{CATALOG}/seed/files")
else:
    BRONZE = DATA / "bronze"
    SEED_DIR = DATA / "seed"

SILVER = DATA / "silver" / "weather_hourly"
QUARANTINE = DATA / "silver" / "quarantine" 
#GOLD = DATA / "gold" / "cooling_modes"
GOLD_FACT_COOLING_HOURS = DATA / "gold" / "fact_cooling_hours"
GOLD_FACT_CITY_YEAR = DATA / "gold" / "fact_city_year"
LOGS = PROJECT_ROOT / "logs"
STAGING = DATA / "staging"
GOLD_DIM_MODE = DATA / "gold" / "dim_mode"
GOLD_DIM_SCENARIO = DATA / "gold" / "dim_scenario"
GOLD_DIM_CITY = DATA / "gold" / "dim_city"
GOLD_DIM_YEAR = DATA / "gold" / "dim_year"

# climate classification
KOPPEN_DIR = DATA / "reference" / "koppen" / "koppen_geiger_tif"
LEGEND_FILE = KOPPEN_DIR/ "legend.txt"
KOPPEN_TIF = KOPPEN_DIR / "1991_2020" / "koppen_geiger_0p1.tif"

# seed
#FLAP-D plus challenger cities -> Group 1
CITIES_FILE = SEED_DIR / "cities.csv" 
CITY_LIST_FILE = SEED_DIR / "city_list.csv"
#global without group 1 
CITIES_GLOBAL_FILE = SEED_DIR / "cities_global.csv"
CITY_LIST_GLOBAL_FILE = SEED_DIR / "city_list_global.csv"
#all cities from 2026 report, categorized in tiers 1-2-3 
CITIES_ALL_FILE = SEED_DIR / "cities_all.csv"
CITIES_LIST_ALL = SEED_DIR / "city_list_all.csv"
#cities with water stress 
CITIES_WATER_STRESS = SEED_DIR / "cities_water_stress.csv"
# mode dimension
DIM_MODE = SEED_DIR / "dim_mode.csv"
DIM_SCENARIO = SEED_DIR / "dim_scenario.csv"
# dimension scenario
SCENARIOS_FILE = SEED_DIR / "dim_scenario.csv"

# Aqueduct Water stress
GDB = DATA /"reference" / "aqueduct" / "GDB"/ "Aq40_Y2023D07M05.gdb"
BWS = DATA /"reference" / "aqueduct" / "CVS" / "Aqueduct40_baseline_monthly_y2023m07d05.csv"


