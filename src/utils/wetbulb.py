from pyspark.sql import Column
from pyspark.sql import functions as F

# standard Stull approximation formula for wet-bulb temperature
# Tw = T·atan(0,151977·(RH + 8,313659)^0,5) + atan(T + RH) − atan(RH − 1,676331) + 0,00391838·RH^1,5·atan(0,023101·RH) − 4,686035


def wet_bulb_stull(temp: Column, rh: Column) -> Column:
    """Wet-bulb temperature (°C) after Stull (2011) from air temperature (°C) and relative humidity (%)."""
    term1 = temp * F.atan(0.151977 * F.pow((rh + 8.313659), 0.5))
    term2 = F.atan(temp + rh)
    term3 = F.atan(rh - 1.676331)
    term4 = 0.00391838 * F.pow(rh, 1.5) * F.atan(0.023101 * rh)

    return term1 + term2 - term3 + term4 - 4.686035
