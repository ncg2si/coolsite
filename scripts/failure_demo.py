""" Failure demo: unusable file got rejected -> watermark stays, the next run recover
run command: COOLSITE_DATA="demo_data" uv run -m scripts.failure_demo
"""

import shutil
from pathlib import Path
import pandas as pd
from datetime import date, datetime, timedelta, timezone
import json

from paths import DATA, BRONZE, SILVER
from transform import transform_city_year
from incremental import get_watermarks, DELAY_DAYS
from spark_utils import get_spark
import ingest
from workflows.incremental_pipeline import run_incremental

REAL_BRONZE = Path(__file__).resolve().parents[1] / "data" / "bronze"
CITY = "frankfurt"
LAT = 50.11
LON = 8.68
if DATA.name != "demo_data":
    raise AssertionError(f"refusing to run on {DATA}") # safety net only run on demo data 
    
# fresh demo folder and copy one real bronze file 

shutil.rmtree(DATA,ignore_errors=True)
source = sorted((REAL_BRONZE / f"city={CITY}").glob("2025-01-01_2025-12-31__fetched_*.json"))[-1]
(BRONZE / f"city={CITY}").mkdir(parents=True)
shutil.copy(source, BRONZE / f"city={CITY}" / source.name)
print(f"copied {source.name}")

# build silver once from bronze data
#(SILVER / f"city={CITY}").mkdir(parents=True)
transform_city_year(CITY,"2025-01-01","2025-12-31")
watermark = get_watermarks(get_spark())
#print(f"watermark = {watermark}")
assert str(watermark.get(CITY))  == "2025-12-31 23:00:00"

# simulation of getting data from API
cities = pd.DataFrame([{"city":CITY, "lat":LAT, "lon": LON}]) 
def fake_api_response(start, end, is_last_day_null): #simulation of delayed data
    """same shape as data responsed from API"""
    times = pd.date_range(start,f"{end} 23:00", freq="h").strftime("%Y-%m-%dT%H:%M").tolist()
    n = len(times)
    temp, rh, dew = [10.0] *n , [80] *n, [7.0] *n
    if is_last_day_null:
        for col in (temp, rh, dew):
            col [-24:] = [None] * 24  # the last 24 hours are None
    return {"latitude": LAT,
            "longitude": LON,
            "timezone": "GMT",
            "hourly": {"time": times, "temperature_2m":temp, "relative_humidity_2m" : rh, "dew_point_2m": dew}}

ingest.time.sleep = lambda s:None # no pauses in the demo

# simulation of incremental loading but last day was not loaded (happened with real data with DELAY_DAYS = 5)
TODAY = date.today()
print(f"Start demo failure incremental load  watermark = {watermark} today is {TODAY}")
ingest.fetch_weather = lambda lat,lon,start,end : fake_api_response(start, end, is_last_day_null= start.startswith("2026")) # only the 2026 window is brokem
failures = run_incremental(cities, today= TODAY)
wm = get_watermarks(get_spark()).get(CITY)
print(f"watermark after incremental load = {wm} ")
print(f"results: {failures}")
assert len(failures) == 1 and "transform" in failures[0]
assert str(wm) == "2025-12-31 23:00:00"                    # unchanged
assert not (SILVER / f"city={CITY}" / "year=2026").exists()

# to simulate that we increased the delay day: 
# set is_last_day_null = False
# change the incremental load to yesterday

YESTERDAY = TODAY-timedelta(days=1)

print(f"Start demo correct incremental load  watermark = {watermark} today is {TODAY}")
ingest.fetch_weather = lambda lat,lon,start,end : fake_api_response(start, end, is_last_day_null= False) # only the 2026 window is brokem
failures = run_incremental(cities, today= YESTERDAY)
wm = get_watermarks(get_spark()).get(CITY)
expected_end = TODAY - timedelta(days=1) - timedelta(days=DELAY_DAYS)
s2026 = get_spark().read.parquet(str(SILVER)).filter(f"city = '{CITY}' AND year = 2026")
print(f"watermark after incremental load = {wm} ")
print(f"results: {failures}")
assert failures == []
assert wm == datetime.combine(expected_end, datetime.min.time()).replace(hour=23)
assert s2026.count() == s2026.select("time").distinct().count()   # no duplicates
print("✅ all demo checks passed")




     





