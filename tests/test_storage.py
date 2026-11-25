import pytest
from pyspark.sql import Row

import storage
from spark_utils import get_spark


@pytest.fixture(scope="module")
def spark():
    return get_spark()


@pytest.fixture
def local_data(tmp_path, monkeypatch):
    """Point storage at a temporary folder, so tests never touch data/."""
    monkeypatch.setattr(storage, "DATA", tmp_path)
    return tmp_path


def rows(spark):
    return spark.createDataFrame([Row(city="berlin", year=2025, v=1),
                                  Row(city="oslo",   year=2025, v=2)])


def test_write_then_read(spark, local_data):
    assert not storage.table_exists(spark, "gold", "t")
    storage.write_table(rows(spark), "gold", "t")
    assert storage.table_exists(spark, "gold", "t")
    assert storage.read_table(spark, "gold", "t").count() == 2


def test_partition_by_creates_folders(spark, local_data):
    storage.write_table(rows(spark), "silver", "q", partition_by=["city", "year"])
    assert (local_data / "silver" / "q" / "city=berlin" / "year=2025").is_dir()


def test_append_adds_rows(spark, local_data):
    storage.write_table(rows(spark), "silver", "q", mode="append")
    storage.write_table(rows(spark), "silver", "q", mode="append")
    assert storage.read_table(spark, "silver", "q").count() == 4