import json
import warnings
from datetime import date
from typing import Literal

from ingest import bronze_path

EXPECT_FIELDS = ("time", "temperature_2m", "relative_humidity_2m", "dew_point_2m")
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

# Structural data quality checks return a severity-message pair or None.

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

def validate(city:str, start:str, end:str) -> None:
    """Run all data quality checks on one bronze file"""
    data = load_bronze(city,start)
    hourly = data["hourly"]
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
    # Checks the rest of the structural data quality rules
    check_results = [
                     check_dq01_row_count(hourly,start,end),
                    check_dq08_timezone_gmt(data)]
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
