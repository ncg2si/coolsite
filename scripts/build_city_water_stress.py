# Script to read the cities list, 
# join with aqueduct data: GDB monthly, yearly and the CSV file (contails pfaf_id)
# write a csv file into CITIES_WATER_STRESS

import pandas as pd
from pandas import DataFrame
import geopandas as gpd
from geopandas import GeoDataFrame
from paths import CITIES_ALL_FILE, CITIES_WATER_STRESS, GDB, BWS




def city_points() -> GeoDataFrame:
    cities = pd.read_csv(CITIES_ALL_FILE)
    return gpd.GeoDataFrame(cities,
                            geometry=gpd.points_from_xy(cities["lon"],cities["lat"],crs="EPSG:4326")
                            )

def join_monthly(points: GeoDataFrame) -> GeoDataFrame:
    basins = gpd.read_file(GDB,layer="baseline_monthly")[["pfaf_id","geometry"]]
    cities_basins = gpd.sjoin(points, basins, how="left", predicate="within")
    cities_basins["pfaf_id"]= cities_basins["pfaf_id"].astype("int")
    bws_monthly = pd.read_csv(BWS)
    cities_bws_monthly = cities_basins.merge(bws_monthly, on="pfaf_id",how="left")
    bws_monthly_cols = [f"bws_{m:02d}_score" for m in range(1,13)]
    cities_bws_score_monthly= cities_bws_monthly.melt(id_vars=["city","pfaf_id"],value_vars=bws_monthly_cols,var_name="col",value_name="bws")
    cities_bws_score_monthly["is_high"] = cities_bws_score_monthly["bws"] >= 4.0
    return cities_bws_score_monthly.groupby(["city"]).agg(bws_months_ge_4 = ("is_high","sum")).reset_index()

def join_annual(points:GeoDataFrame)-> GeoDataFrame:
    bws_cols = ["pfaf_id","geometry", "bws_score","bws_cat","bws_label"]
    bws_yearly = gpd.read_file(GDB,layer="baseline_annual")[bws_cols]
    bws_yearly["bws_cat"] = bws_yearly["bws_cat"].astype("Int64")
    return gpd.sjoin(points, bws_yearly, how="left", predicate="within")[["city"] + bws_cols ]

if __name__ == "__main__":
    points = city_points()
    cities_bws_monthly = join_monthly(points)
    cities_bws_yearly = join_annual(points)
    cities_bws_yearly = cities_bws_yearly.rename(columns={"bws_score": "bws_annual_score", "bws_cat": "bws_annual_cat", "bws_label":"bws_annual_label"})
    cities_bws = cities_bws_monthly.merge(cities_bws_yearly, how='left', on="city", validate='1:1')
    cities_bws = cities_bws.drop("geometry",axis=1)
    cities_bws = cities_bws[["city", "pfaf_id", "bws_annual_score", "bws_annual_cat", "bws_annual_label", "bws_months_ge_4"]]
    assert len(cities_bws) == 106
    cities_bws.to_csv(CITIES_WATER_STRESS,index=False)
    