""" Read and write tables 
Parquet folders locally – Delta tables in Unity Catalog on Databricks
"""

from pyspark.sql import DataFrame, SparkSession
from paths import ON_DATABRICKS, CATALOG, DATA
from pathlib import Path

def table_name(layer:str, name:str)-> str:
    """Return Unity Catalog name"""
    return f"{CATALOG}.{layer}.{name}"

def local_path(layer: str, name:str)-> str:
    """Local parquet folder"""
    return (DATA / layer / name)

def write_table(df:DataFrame, layer:str, name:str,mode: str="overwrite")-> None:
    if ON_DATABRICKS:
        (df.write.format("delta").mode(mode)
            .option("overwriteSchema","true") 
            .saveAsTable(table_name(layer,name))
         )
    else:
        df.write.mode(mode).parquet(local_path(layer,name))

def read_table(spark:SparkSession,layer:str,name:str)-> DataFrame:
    if ON_DATABRICKS:
        return spark.table(table_name(layer,name))
    return spark.read.parquet(local_path(layer,name))

def table_exists(spark:SparkSession, layer:str, name:str)-> bool:
    if ON_DATABRICKS:
        return spark.catalog.tableExists(table_name(layer,name))
    return Path(local_path(layer,name)).exists()
