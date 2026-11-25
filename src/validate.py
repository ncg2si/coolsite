import json
import warnings
from datetime import date
from typing import Literal
from pathlib import Path

import pyspark.sql.functions as F
from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql.window import Window

from contract import (
    EXPECT_FIELDS,
    EXPECT_TIMEZONE,
    MAX_UNUSABLE_HOURS_PER_FILE,
    ROW_RULES,
)
from ingest import latest_bronze_path
from spark_utils import get_spark, read_bronze_hourly
from utils.log import get_logger

log = get_logger(Path(__file__).stem)

CheckResult = tuple[Literal["error", "warning"], str] | None


def parse_date_range(start: str, end: str) -> tuple[date, date]:
    """Check that start/end are real dates (YYYY-MM-DD) and start <= end.
    Raises ValueError with a clear message otherwise."""
    try:
        start_d = date.fromisoformat(start)
    except ValueError:
        raise ValueError(f"invalid start date {start!r}, expected YYYY-MM-DD") from None
    try:
        end_d = date.fromisoformat(end)
    except ValueError:
        raise ValueError(f"invalid end date {end!r}, expected YYYY-MM-DD") from None
    if start_d > end_d:
        raise ValueError(f"start date {start} is after end date {end}")
    return start_d, end_d

def load_bronze(path: Path) -> dict:
    """Read one bronze file and return the raw API dict"""
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
    """DQ-02: timezone must be EXPECT_TIMEZONE"""
    if data["timezone"] != EXPECT_TIMEZONE:
        return ("error", f"DQ-02 failed: timezone is {data['timezone']}, contract expects {EXPECT_TIMEZONE}")

# Dataset rules
# Answer the question: "Is the whole set complete and consistent?"
# Fail or warn

def range_bounds(start: str, end: str) -> tuple[Column, Column]:
    """First and last expected hour: start 00:00 and end 23:00 (session time = UTC)."""
    first = F.to_timestamp(F.lit(f"{start} 00:00:00"))
    last = F.to_timestamp(F.lit(f"{end} 23:00:00"))
    return first, last

def in_range(start: str, end: str) -> Column:
    """True if the hour lies inside the expected range (both ends included)."""
    first, last = range_bounds(start, end)
    return F.col("time").between(first, last)

def check_dq03_time_range(df: DataFrame, start: str, end: str) -> tuple[CheckResult, int, int]:
    """DQ-03: hours must cover start 00:00 ... end 23:00.
    - hours outside the range -> warning (excluded from silver, NOT unusable)
    - hours missing at the edges -> warning + returned as unusable hours (budget: validate step 6)
    - no hour inside the range -> error
    - more or less than one city in the data -> error (assumption: one bronze file = one city)
    Returns (result, missing_edge_hours, outside_hours)."""
    first, last = range_bounds(start, end)
    inside = in_range(start, end)
    time_in = F.when(inside,F.col("time"))
    row = df.agg(
        F.count_distinct("city").alias("n_cities"),
        F.sum(F.when(~inside,1).otherwise(0)).alias("outside"),
        ((F.min(time_in).cast("long")-first.cast("long"))/3600).cast("int").alias("missing_head"),
        ((last.cast("long") - F.max(time_in).cast("long")) / 3600).cast("int").alias("missing_tail")
    ).first()
    n_cities= row["n_cities"]
    if n_cities != 1:
        return ("error", f"DQ-03 failed: expected exactly 1 city per file, found {n_cities}"), 0, 0
    n_outside = row["outside"]
    if row["missing_head"] is None:
        return ("error", f"DQ-03 failed: no hours between {start} 00:00 and {end} 23:00"), 0, n_outside
    issues = []
    if n_outside:
        issues.append(f"{n_outside} hour(s) outside the range, excluded from silver")
    if row["missing_head"]:
        issues.append(f"{row["missing_head"]} hour(s) missing at the start")
    if row["missing_tail"]:
        issues.append(f"{row['missing_tail']} hour(s) missing at the end")
    missing = row["missing_head"] + row["missing_tail"]
    if issues:
        return ("warning", "DQ-03 warning: " + "; ".join(issues)), missing, n_outside
    return None, 0, n_outside

# Helper functions for dq04 check
def drop_identical(df:DataFrame) -> DataFrame:
    """Keep one copy of rows that are identical in every column"""
    return df.dropDuplicates()
def find_conflicting_hours(deduped:DataFrame) -> DataFrame:
    """Conflicting hours (same time but different value)"""
    return(deduped.groupBy("city","time").count()
           .filter(F.col("count")>1)
           .select("city","time")
           )
def check_dq04_no_duplicates_hour(df: DataFrame) -> tuple[CheckResult, int]:
    """DQ-04: no duplicate hours.
    - identical copies → warning, one copy kept
    - same hour, different values → warning, all copies to quarantine, hour counts as unusable
    Returns (result, conflicting_hours):
        result            -- ("warning", message) if duplicates were found, otherwise None
        conflicting_hours -- number of hours with conflicting values (unusable, for the error budget)"""
    deduped = drop_identical(df)
    n_identical = df.count() - deduped.count()
    n_conflicting = find_conflicting_hours(deduped).count()
    issues = []
    if n_identical:
        issues.append(f"{n_identical} identical duplicate row(s) removed")
    if n_conflicting:
        issues.append(f"{n_conflicting} hour(s) with conflicting values moved to quarantine")
    if issues:
        return("warning", "DQ-04 warning: " + "; ".join(issues)), n_conflicting
    return None,0

def split_duplicates(df:DataFrame) -> tuple[DataFrame, DataFrame]:
    """Return (clean, quarantine).
    clean: identical copies reduced to one, conflicting hours removed.
    quarantine: all copies of conflicting hours, failed_rules = ['DQ-04']."""
    deduped = drop_identical(df)
    conflicting = find_conflicting_hours(deduped)
    clean = deduped.join(conflicting , on=["city","time"], how="left_anti")
    quarantine = (deduped.join(conflicting, on = ["city","time"], how ="left_semi")
                  .withColumn("failed_rules", F.array(F.lit("DQ-04")))
                  )
    return clean, quarantine
        

def check_dq05_hourly_steps(df: DataFrame) -> tuple[CheckResult, int]:
    """DQ-05: consecutive hours must be exactly 1 h apart (no gaps, no off-grid times).
    Duplicates (diff 0) are ignored here, they belong to DQ-04.
    Returns (result, missing_hours):
        result        -- ("warning", message) if at least one step is not 1 h, otherwise None
        missing_hours -- number of hours missing inside the range (unusable, for the error budget)"""
    w = Window.partitionBy("city").orderBy("time")
    steps = (df.withColumn("prev_time", F.lag("time").over(w))
            .withColumn("diff_seconds",F.col("time").cast("long") - F.col("prev_time").cast("long"))
            .filter(F.col("diff_seconds").isNotNull() & (F.col("diff_seconds") != 0)))
    stats = steps.agg(
        F.coalesce(F.sum(F.when((F.col("diff_seconds") > 3600) & (F.col("diff_seconds") % 3600 == 0),
                                F.col("diff_seconds") / 3600 - 1)), F.lit(0)).cast("int").alias("missing_hours"),
        F.sum(F.when(F.col("diff_seconds") % 3600 != 0, 1).otherwise(0)).alias("off_grid_steps"),
    ).first()
    missing_hours = stats["missing_hours"]
    off_grid = stats["off_grid_steps"] or 0
    issues = []
    if missing_hours:
        issues.append(f"{missing_hours} hour(s) missing inside the range")
    if off_grid:
        issues.append(f"{off_grid} step(s) not on the full hour")
    if issues:
        return ("warning", "DQ-05 warning: " + "; ".join(issues)), missing_hours
    return None, 0
    
# Content data quality checks 
# Row rules and answer the question "Is this row valid?"
# On Failure quarantine the bad rows, good rows continue

def apply_row_rules(df:DataFrame, rules: dict[str,str]) -> tuple[DataFrame,DataFrame]:
    """Split rows into valid and quarantined. Quarantined rows list the rule IDs they broke."""
    failed =(F.array_compact(F.array(
         *[ F.when(~F.coalesce(F.expr(condition),F.lit(True)),F.lit(rule_id)) for rule_id, condition in rules.items()])))
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
        log.warning(message)
        warnings.warn(message, UserWarning, stacklevel=2)
    else: 
        raise ValueError(f"Unknown check severity: {severity!r}")


# Validate the bronze file for one city and one start date. 
# Separate validation


def validate(city: str, start: str, end: str) -> tuple[DataFrame, DataFrame, dict]:
    """Run all DQ checks on one bronze file. 
    Return (valid rows, quarantined rows, number of valid rows and number of quarantined rows)."""
    start_d, end_d = parse_date_range(start,end)
    start, end = start_d.isoformat(), end_d.isoformat()   # luôn là "2025-12-31"
    path = latest_bronze_path(city, start, end)
    if path is None:
        raise FileNotFoundError(f"no bronze file for {city} {start}...{end}")
    data = load_bronze(path)
    hourly = data["hourly"]
    problems, warnings_list = [], []

    # 1. GATE
    collect(check_dq01_required_fields_present(hourly), problems, warnings_list)
    collect(check_dq02_timezone_gmt(data), problems, warnings_list)
    if problems:
        raise ValueError("Schema gate failed, other checks skipped:\n" + "\n".join(problems))
    # 2. SPARK READ (only after the gate)
    spark = get_spark()
    
    raw = read_bronze_hourly(spark, str(path), city).cache()
    # 3. DATASET RULES (DQ-03 on the full data, then drop the out-of-range rows)
    try:
        n_read = raw.count()                                     # all rows from bronze (for the balance check)
        dq03_result, missing_edge_hours, n_excluded = check_dq03_time_range(raw, start, end)
        collect(dq03_result, problems, warnings_list)
        raw = raw.filter(in_range(start, end))                    # out-of-range rows never reach DQ-04/05 or silver
        #n_excluded = n_read - raw.count()
        # 4. MORE DATASET RULES: each returns (result, unusable hours)
        dq04_result, conflicting_hours = check_dq04_no_duplicates_hour(raw)
        collect(dq04_result,problems,warnings_list)
        # Check for DQ05 (gaps) first before removing duplicates:
        dq05_result, n_missing_hours = check_dq05_hourly_steps(raw)
        collect(dq05_result, problems, warnings_list)
    
        # remove identical duplicates and move conflicting hours to quarantine

        clean, dup_quarantine = split_duplicates(raw)
        clean = clean.cache()
    
    
        # 5. ROW RULES
        valid, quarantine = apply_row_rules(clean, ROW_RULES)
        n_in, n_valid, n_quarantine = clean.count(), valid.count(), quarantine.count()
        if n_valid + n_quarantine != n_in:
            problems.append(f"Error occured while applying row rules {ROW_RULES}")
    
        # 6. DECIDE
        # Unusable hours = missing hours (DQ-03 at the edges / DQ-05 inside) + 
        # quarantined rows (DQ-06, DQ-07, DQ-08, DQ-09) + 
        # hours with conflicting duplicates (DQ-04)
        quarantine = quarantine.unionByName(dup_quarantine)
        unusable_hours = (missing_edge_hours + n_missing_hours + conflicting_hours + n_quarantine ) 
        n_total_quarantine = quarantine.count()
        if unusable_hours > MAX_UNUSABLE_HOURS_PER_FILE:
            problems.append(f"{unusable_hours} hour(s) unusable exceeded budget of {MAX_UNUSABLE_HOURS_PER_FILE} unusable hours per file")
        elif unusable_hours > 0:
            collect(("warning", f"{unusable_hours} unusable hour(s), within budget"), problems, warnings_list)
        if problems:
            raise ValueError("Validation failed:\n" + "\n".join(problems))

        # 7. SUMMARY: one line, all numbers (the guide asks for this)
        log.info(f"{city} {start}: rows_read={n_read} excluded={n_excluded} rows_in={n_in} valid={n_valid} "
            f"quarantined={n_total_quarantine} warnings={len(warnings_list)}")

        # 8. RETURN
        stats = {"n_valid":n_valid,"n_quarantine": n_total_quarantine}
        return valid, quarantine, stats
    finally:
        raw.unpersist()


if __name__ == "__main__":
    start = "2025-01-01"
    end = "2025-12-31"
    

    #validate(city="frankfurt", start=start, end=end)
    validate(city="barcelona", start=start, end=end)