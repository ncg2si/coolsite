from datetime import datetime

import pytest

import transform
from spark_utils import get_spark


@pytest.fixture(scope="module")
def spark():
    return get_spark()


def rows_to_df(spark, rows):
    return spark.createDataFrame(
        rows, "city string, year int, time timestamp, temperature_c double"
    )


def test_upsert_new_wins_old_kept(spark, tmp_path, monkeypatch):
    monkeypatch.setattr(transform, "SILVER", tmp_path / "silver")
    monkeypatch.setattr(transform, "STAGING", tmp_path / "staging")

    # silver before: 3 hours
    old = rows_to_df(
        spark,
        [
            ("test_city", 2026, datetime(2026, 1, 1, 0), 1.0),
            ("test_city", 2026, datetime(2026, 1, 1, 1), 2.0),
            ("test_city", 2026, datetime(2026, 1, 1, 2), 3.0),
        ],
    )
    transform.write_partitioned(old, str(tmp_path / "silver"))

    # new batch: hour 2 corrected (3.0 → 30.0) + hour 3 new
    new = rows_to_df(
        spark,
        [
            ("test_city", 2026, datetime(2026, 1, 1, 2), 30.0),
            ("test_city", 2026, datetime(2026, 1, 1, 3), 4.0),
        ],
    )
    transform.upsert_silver(new, "test_city", 2026)

    result = {
        r["time"].hour: r["temperature_c"]
        for r in spark.read.parquet(str(tmp_path / "silver")).collect()
    }
    assert result == {0: 1.0, 1: 2.0, 2: 30.0, 3: 4.0}
