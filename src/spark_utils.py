from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from contract import EXPECT_FIELDS, COLUMN_MAP
from paths import ON_DATABRICKS




def get_spark() -> SparkSession:
    """ A local/databricks spark session """
    if ON_DATABRICKS:
        spark = SparkSession.builder.getOrCreate()
        spark.conf.set("spark.sql.session.timeZone","UTC")
        return spark
    return (SparkSession.builder
            .appName("coolsite")
            .master("local[*]")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.driver.memory", "4g")
            .getOrCreate())
def read_bronze_hourly(spark: SparkSession, path: str, city: str) -> DataFrame:
    """Read a bronze JSON file -> one row per hour."""  
    raw = spark.read.json(str(path),multiLine=True)
    cols = [F.col(f"hourly.{field}") for field in EXPECT_FIELDS]
    data_transformed = (raw.select(F.explode(F.arrays_zip(*cols)).alias("h")).select("h.*")
                                    .withColumnsRenamed(COLUMN_MAP)
                                    .withColumn("time", F.to_timestamp("time","yyyy-MM-dd'T'HH:mm"))
                                    .withColumn("city",F.lit(city))
    )
    return data_transformed
