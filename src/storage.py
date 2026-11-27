"""Read and write tables
Parquet folders locally – Delta tables in Unity Catalog on Databricks
"""

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from paths import CATALOG, DATA, ON_DATABRICKS


def table_name(layer: str, name: str) -> str:
    """Return Unity Catalog name"""
    return f"{CATALOG}.{layer}.{name}"


def local_path(layer: str, name: str) -> str:
    """Local parquet folder"""
    return str(DATA / layer / name)


def write_table(
    df: DataFrame, layer: str, name: str, mode: str = "overwrite", partition_by=None
) -> None:
    if (
        ON_DATABRICKS
    ):  # no partition on Databricks to prevent too many small files (small data < 1TB)
        (
            df.write.format("delta")
            .mode(mode)
            .option("overwriteSchema", "true")
            .saveAsTable(table_name(layer, name))  # Delta table
        )
    else:
        writer = df.write.mode(mode)
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        writer.parquet(local_path(layer, name))


def read_table(spark: SparkSession, layer: str, name: str) -> DataFrame:
    if ON_DATABRICKS:
        return spark.table(table_name(layer, name))
    return spark.read.parquet(local_path(layer, name))


def table_exists(spark: SparkSession, layer: str, name: str) -> bool:
    if ON_DATABRICKS:
        return spark.catalog.tableExists(table_name(layer, name))
    return Path(local_path(layer, name)).exists()


def merge_into(
    spark, df, layer, name, keys
):  # only on Databricks, for local runs use upsert_silver
    """Upsert rows with the same keys are replaced, new keys are inserted (Delta MERGE)"""
    from delta.tables import DeltaTable

    if not table_exists(spark, layer, name):
        write_table(df, layer, name)  # first run, create the table
        return
    target = DeltaTable.forName(spark, table_name(layer, name))
    condition = " AND ".join(
        f"t.{key} = s.{key}" for key in keys
    )  # t.city = s.city, t.time = s.time
    (
        target.alias("t")
        .merge(df.alias("s"), condition)
        .whenMatchedUpdateAll()  # same city,time new values win
        .whenNotMatchedInsertAll()  # new hour: insert
        .execute()
    )
