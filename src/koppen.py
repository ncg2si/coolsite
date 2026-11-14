
from paths import KOPPEN_DIR, LEGEND_FILE, KOPPEN_TIF
import rasterio 


# with open(LEGEND_FILE,encoding="utf-8") as f:
#     for line in f:
#         print(repr(line))

def load_legend(path=LEGEND_FILE) -> dict [int,dict[str,str]]:
    """Read the Köppen legend file (Beck et al. 2023) """
    legend = {}
    with open (LEGEND_FILE,encoding="utf-8") as f:
        for line in f:
            line = line.strip() # remove spaces at both ends and the \n
            if not line[:1].isdigit(): # header, empty line or citation → skip
                continue
            code, rest = line.split(":",1) # split only at the FIRST ":"
            before_bracket = rest.split("[")[0].strip()
            climate_class, description = before_bracket.split(maxsplit=1)   
            legend[int(code)] = {"code": int(code), "class": climate_class, "description": description}
    return legend

def koppen_at(tif_path, lat: float, lon: float, legend: dict) -> dict | None:
    """Köppen class + description at one point, or None if the pixel has no class (e.g. sea)."""
    with rasterio.open(tif_path) as src:
        value = next(src.sample([(lon, lat)]))[0] 
    return legend.get(int(value))



if __name__ == "__main__":
    legend = load_legend()
    frankfurt_climate = koppen_at(KOPPEN_TIF, 50.11,8.68, legend) 
    barcelona_climate = koppen_at(KOPPEN_TIF, 41.3888,2.159, legend)
    print(frankfurt_climate)