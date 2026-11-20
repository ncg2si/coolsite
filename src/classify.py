from pyspark.sql import DataFrame, Column, functions as F

# Simple version for now → move to config/settings.yaml later. All values illustrative, see decision log.
DEFAULT_PARAMS = {
    "A": 27.0,          # max supply air temperature (°C), ASHRAE recommended upper limit
    "dew_max": 15.0,    # ASHRAE recommended max dew point (°C)
    "dew_min": -9.0,    # ASHRAE recommended min dew point (°C)
    "eps_evap": 0.8,    # evaporative effectiveness (example, to source)
    "eps_hx": 0.7,      # heat-exchanger effectiveness, indirect design (example, Park & Seo 2018)
    "T_return": 37.0,   # return air temperature from servers(°C), indirect design (example, to source)
    "evap_assist": True,   # can evaporative pre-cooling run together with the chiller?
}


def classify(df: DataFrame, design: str = "direct", p: dict = DEFAULT_PARAMS) -> DataFrame:
    """Give every hour exactly one cooling mode: free / evaporative / chiller / hybrid"""
    T, Tw, Td = F.col("temperature_c"), F.col("wet_bulb_c"), F.col("dew_point_c")

    if design == "direct":
        a = p["A"]
        humidity_limited = Td > p["dew_max"]
        too_dry = Td < p["dew_min"]
    elif design == "indirect":
        a = p["T_return"] - (p["T_return"] - p["A"]) / p["eps_hx"]
        humidity_limited = F.lit(False)     # outside air never enters the room
        too_dry = F.lit(False) # outside air never enters the room
    else:
        raise ValueError(f"unknown design {design!r}, expected 'direct' or 'indirect'")

    supply_after_evap = T - p["eps_evap"] * (T - Tw) # temperature after evaporative cooling     
    mode = (F.when(humidity_limited, "chiller")
             .when(T < a, "free")
             .when(supply_after_evap <= a, "evaporative")
             .when(F.lit(p["evap_assist"]), "hybrid")     # evaporative pre-cooling + chiller trim
             .otherwise("chiller"))
    # to count the degree-hours for evap cooling and chiller cooling. Proxy number to measure how much and 
    # for how long — temperature stays above base line level (threshold)
    water_degree = (F.when(mode == "evaporative", T - F.lit(a))
                    .when(mode=="hybrid",T-supply_after_evap)
                    .otherwise(F.lit(0.0)))
    chiller_degree = (F.when(mode == "chiller",F.greatest(T-F.lit(a),F.lit(0.0)))
                      .when(mode == "hybrid", supply_after_evap-F.lit(a))
                      .otherwise(F.lit(0.0)))

    return (df.withColumn("design", F.lit(design))
              .withColumn("mode", mode)
              .withColumn("humidity_limited", humidity_limited)
              .withColumn("too_dry", too_dry)
              .withColumn("water_degree", water_degree)
              .withColumn("chiller_degree", chiller_degree)
              )