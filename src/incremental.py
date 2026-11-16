from datetime import datetime, timezone,date, timedelta
from paths import SILVER
from pyspark.sql import functions as F

LOOKBACK_DAYS = 7
DELAY_DAYS = 7 # ERA5 - Land arrives 5 days late -> 7 for safety
FIRST_DAY = date(1961,1,1)


def fetch_window(watermark: datetime | None, today: date) -> tuple[date,date]:
    """Return (start, end) date to fetch. watermark = None -> new city -> FIRSTDAY """
    if watermark is None:
        start = FIRST_DAY
    else:
        start = (watermark - timedelta(days = LOOKBACK_DAYS)).date()
    end = today - timedelta(days=DELAY_DAYS)
    return start, end

def split_by_year(start: date, end: date) -> list[tuple[date,date]]:
    """ Split time window (start,end) into chunks that each stay inside one calendar year """  
    chunks = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(date(chunk_start.year,12,31),end)
        chunks.append((chunk_start,chunk_end))
        chunk_start = chunk_end+ timedelta(days=1)
    return chunks

def get_watermarks(spark) -> dict:
    """Latest hour in silver per city: {city: datetime}. Cities without data are not in the dict."""
    rows = (spark.read.parquet(str(SILVER))
            .groupBy("city")
            .agg(F.max("time").cast("timestamp_ntz").alias("watermark")) # cast to no time zone to use the session timezone
            .collect())
    return {r["city"]: r["watermark"] for r in rows}






if __name__ == "__main__":
    from spark_utils import get_spark
    spark = get_spark()
    wm = get_watermarks(spark)
    print(len(wm))
    print(wm.get("atlanta"))
    print(wm.get("berlin"))
