import json
import warnings
from datetime import date
from typing import Literal

import pyspark.sql.functions as F
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.window import Window

from contract import EXPECT_FIELDS, ROW_RULES
from ingest import bronze_path
from spark_utils import get_spark, read_bronze_hourly

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

def check_dq01_required_fields_present(hourly:dict) -> CheckResult:
    """DQ-01: missing fields are errors; fields outside the contract are warnings."""
    missing = set(EXPECT_FIELDS) - set(hourly.keys())
    unexpected = set(hourly.keys()) - set(EXPECT_FIELDS)
    if missing:
        return ("error", f"DQ-01 failed: missing fields {missing}")
    if unexpected:
        return ("warning", f"DQ-01 warning: unexpected fields {unexpected}")

def check_dq02_timezone_gmt(data:dict) -> CheckResult:
    """DQ-02: timezone must be GMT"""
    if data["timezone"] != "GMT":
        return ("error", f"DQ-02 failed: timezone is {data['timezone']}, contract expects GMT")

# Dataset rules
# Answer the question: "Is the whole set complete and consistent?"
# Fail or warn

def check_dq03_row_count(hourly:dict, start:str, end:str) -> CheckResult:
    """DQ-03: number of hours must equal inclusive days x24"""
    actual = len(hourly["time"])
    expected = inclusive_days(start,end) * 24
    if actual != expected:
        return ("error", f"DQ-03 failed: file has {actual} hours, contract expects {expected}")

def check_dq04_no_duplicates_hour(df: DataFrame) -> tuple[CheckResult, DataFrame]:
    """DQ-04: no duplicates of hours per city"""
    duplicates = df.groupBy("city","time").agg(F.count("*").alias("count")).filter(F.col("count")>1)
    n_dups = duplicates.count()
    if n_dups > 0:
        return ("error", f"DQ-04 error: {n_dups} row(s) duplicated"), duplicates
    return None, duplicates

def check_dq05_hourly_steps(df: DataFrame) -> tuple[CheckResult, DataFrame] | None:
    """ DQ-05: consecutive hours must be exactly 1h apart, increasing"""
    w = Window.partitionBy("city").orderBy("time")
    gaps = (df.withColumn("prev_time", F.lag("time").over(w))
            .withColumn("diff_seconds",F.col("time").cast("long") - F.col("prev_time").cast("long"))
            .filter((F.col("diff_seconds") != 3600) & (F.col("diff_seconds") != 0) ))  #first gap NULL isn't a gap, duplicates rows counted in a different rule
    n_gaps = gaps.count()
    if n_gaps>0:
        return ("error", "DQ-05 warning: violated exactly 1h step rule"), gaps
    return None, gaps
    
# Content data quality checks 
# Row rules and answer the question "Is this row valid?"
# On Failure quarantine the bad rows, good rows continue

def apply_row_rules(df:DataFrame, rules: dict[str,str]) -> tuple[DataFrame,DataFrame]:
    """Split rows into valid and quarantined. Quarantined rows list the rule IDs they broke."""
    failed =(F.array_compact(F.array(
         *[ F.when(~F.coalesce(F.expr(condition),F.lit(True)),F.lit(rule_id))  for rule_id, condition in rules.items()])))
    checked = df.withColumn("failed_rules", failed)
    valid = checked.filter(F.size("failed_rules") ==0).drop("failed_rules")
    quarantine = checked.filter(F.size("failed_rules")>0)
    return valid, quarantine
          
def collect(result: CheckResult, problems: list[str], warning_lists: list[str]) -> None:
    """Sort one check result into problems or warnings. None = passed."""
    if result is None:
        return
    severity, message = result
    if severity == "error":
        problems.append(message)
    elif severity == "warning":
        warning_lists.append(message)
        warnings.warn(message, UserWarning, stacklevel=2)
    else: 
        raise ValueError(f"Unknown check severity: {severity!r}")


# Validate the bronze file for one city and one start date. Raise ValueError if any check fails.
MAX_QUARANTINE_SHARE = 0.01   # error budget: more than 1 % bad rows = something systematic

def validate(city: str, start: str, end: str) -> tuple[DataFrame, DataFrame]:
    """Run all DQ checks on one bronze file. Return (valid rows, quarantined rows)."""
    data = load_bronze(city, start)
    hourly = data["hourly"]
    problems, warnings_list = [], []

    # 1. GATE
    collect(check_dq01_required_fields_present(hourly), problems, warnings_list)
    if problems:
        raise ValueError("Schema gate failed, other checks skipped:\n" + "\n".join(problems))

    # 2. STRUCTURE
    collect(check_dq03_row_count(hourly, start, end), problems, warnings_list)
    if problems:
        raise ValueError("Schema gate failed, other checks skipped:\n" + "\n".join(problems))

    # 3. SPARK READ (only after the gate)
    spark = get_spark()
    df = read_bronze_hourly(spark, str(bronze_path(city, start)), city)

    # 4. DATASET RULES: each returns (result, rows); keep the result, the rows are for the log
    dq04_result, duplicates = check_dq04_no_duplicates_hour(df)
    collect(dq04_result, problems, warnings_list)
    

    # 5. ROW RULES
    valid, quarantine = apply_row_rules(df, ROW_RULES)
    n_in, n_valid, n_quarantine = df.count(), valid.count(), quarantine.count()
    # TODO: check that n_valid + n_quarantine == n_in  (otherwise: a bug in the split → error)

    # 6. DECIDE
    # TODO: if n_quarantine / n_in > MAX_QUARANTINE_SHARE → add an error to problems
    if problems:
        raise ValueError("\n".join(problems))

    # 7. SUMMARY: one line, all numbers (the guide asks for this)
    print(f"{city} {start}: rows_in={n_in} valid={n_valid} "
          f"quarantined={n_quarantine} warnings={len(warnings_list)}")

    # 8. RETURN
    return valid, quarantine





if __name__ == "__main__":
    start = "2026-06-01"
    end = "2026-09-01"
    validate(city="frankfurt", start=start, end=end)
