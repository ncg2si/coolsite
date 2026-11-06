import json
import warnings
from datetime import date
from typing import Literal
from ingest import bronze_path
from pyspark.sql import DataFrame, SparkSession
from spark_utils import get_spark, read_bronze_hourly
from contract import EXPECT_FIELDS

CheckResult = tuple[Literal["error", "warning"], str] | None

def load_bronze(city:str, start:str) -> dict:
    """Read one bronze file and return the raw API dict"""
    path = bronze_path(city,start)
    return json.loads(path.read_text())

def inclusive_days(start:str, end:str) -> int:
    """Count calendar days from start to end both dates included"""
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    return (end_d - start_d).days +1

# Structural data quality checks (gate) return a severity-message pair or None. 
# Answer the question: "Is the file usable at all?"
# On failure stop the run, bronze is kept

def check_dq01_row_count(hourly:dict, start:str, end:str) -> CheckResult:
    """DQ-01: number of hours must equal inclusive days x24"""
    actual = len(hourly["time"])
    expected = inclusive_days(start,end) * 24
    if actual != expected:
        return ("error", f"DQ-01 failed: file has {actual} hours, contract expects {expected}")

def check_dq08_timezone_gmt(data:dict) -> CheckResult:
    """DQ-08: timezone must be GMT"""
    if data["timezone"] != "GMT":
        return ("error", f"DQ-08 failed: timezone is {data['timezone']}, contract expects GMT")

def check_dq09_required_fields_present(hourly:dict) -> CheckResult:
    """DQ-09: missing fields are errors; fields outside the contract are warnings."""
    missing = set(EXPECT_FIELDS) - set(hourly.keys())
    unexpected = set(hourly.keys()) - set(EXPECT_FIELDS)
    if missing:
        return ("error", f"DQ-09 failed: missing fields {missing}")
    if unexpected:
        return ("warning", f"DQ-09 warning: unexpected fields {unexpected}")

# Content data quality checks 
# Row rules and answer the question "Is this row valid?"
# On Failure quarantine the bad rows, good rows continue

def check_dq05_humidity_range(spark: SparkSession, df: DataFrame ) -> tuple[CheckResult, DataFrame]:
    """DQ-05: relative humidity must be between 0 and 100 %."""
    df.createOrReplaceTempView("bronze_hourly")
    bad_rows = spark.sql(""" 
        SELECT *
        FROM bronze_hourly
        WHERE relative_humidity_2m < 0 OR relative_humidity_2m > 100  -- comparison with NULL return NULL, DQ-02 checks for NULL
    """)
    n_bad = bad_rows.count()
    if n_bad > 0:
        return ("error", f"DQ-05 failed: {n_bad} rows with humidity outside 0-100%"), bad_rows
    

# Validate the bronze file for one city and one start date. Raise ValueError if any check fails.
def validate(city:str, start:str, end:str) -> None:
    """Run all data quality checks on one bronze file"""
    data = load_bronze(city,start)
    hourly = data["hourly"]
    spark = get_spark()
    path = bronze_path(city,start)
    df = read_bronze_hourly(spark, str(path), city)

    # --- GATE: Check schema first---
    schema_result = check_dq09_required_fields_present(hourly)
    if schema_result is not None:
        severity, message = schema_result
        if severity == "error":
            raise ValueError(message)
        elif severity == "warning":
            warnings.warn(message, UserWarning, stacklevel=2)
        else:
            raise ValueError(f"Unknown check severity: {severity!r}")
    # Checks the rest of the structural data quality rules then the content data quality rules
    check_results = [
                     check_dq01_row_count(hourly,start,end),
                    check_dq08_timezone_gmt(data),
                    check_dq05_humidity_range(spark,df)[0]
                    ]
    problems = []
    warning_messages = []
    for result in check_results:
        if result is None:
            continue
        severity, message = result
        if severity == "error":
            problems.append(message)
        elif severity == "warning":
            warning_messages.append(message)
            warnings.warn(message, UserWarning, stacklevel=2)
        else:
            raise ValueError(f"Unknown check severity: {severity!r}")

    if problems:
        raise ValueError("\n".join(problems))
    elif warning_messages:
        print(f"{city} {start}: All checks completed with warnings")
    else:
        print(f"{city} {start} : All {len(check_results)+1} checks passed")

if __name__ == "__main__":
    start = "2026-06-01"
    end = "2026-09-01"
    validate(city="frankfurt", start=start, end=end)
