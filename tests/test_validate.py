import json

import pytest

import validate  # validate() tested on fake (broken) bronze files

DAY = "2026-06-01"


# ---------------------------------------------------------------------------
# Helpers (not tests: they don't start with test_)
# ---------------------------------------------------------------------------

def good_hourly():
    """24 clean hours in the raw Open-Meteo format."""
    return {
        "time": [f"{DAY}T{h:02d}:00" for h in range(24)],
        "temperature_2m": [18.0] * 24,
        "relative_humidity_2m": [70] * 24,
        "dew_point_2m": [12.6] * 24,
    }


def add_hour(hourly, time, temperature=18.0, humidity=70, dew_point=12.6):
    """Append one extra hour to all four lists (they must stay the same length)."""
    hourly["time"].append(time)
    hourly["temperature_2m"].append(temperature)
    hourly["relative_humidity_2m"].append(humidity)
    hourly["dew_point_2m"].append(dew_point)


def write_bronze(tmp_path, hourly, timezone="GMT"):
    """Write a fake API response as a bronze file and return its path."""
    path = tmp_path / "bronze.json"
    path.write_text(json.dumps({"timezone": timezone, "hourly": hourly}))
    return path


def run_validate(tmp_path, monkeypatch, hourly):
    """Write the fake file, point validate() at it, run it for one day."""
    path = write_bronze(tmp_path, hourly)
    monkeypatch.setattr(validate, "bronze_path", lambda city, start: path)
    return validate.validate("frankfurt", DAY, DAY)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_write_bronze_creates_a_readable_file(tmp_path):
    path = write_bronze(tmp_path, good_hourly())
    raw = json.loads(path.read_text())
    assert raw["timezone"] == "GMT"
    assert len(raw["hourly"]["time"]) == 24


def test_missing_field_stops_the_run(tmp_path, monkeypatch):
    hourly = good_hourly()
    del hourly["dew_point_2m"]                      # break it: one field missing

    with pytest.raises(ValueError, match="DQ-01 failed"):
        run_validate(tmp_path, monkeypatch, hourly)


def test_extra_field_only_warns(tmp_path, monkeypatch):
    hourly = good_hourly()
    hourly["extra_field"] = [5.0] * 24              # break it: one extra field

    with pytest.warns(UserWarning, match="DQ-01 warning"):
        valid, quarantine = run_validate(tmp_path, monkeypatch, hourly)

    assert valid.count() == 24                      # the run continued with all good hours


def test_conflicting_hour_goes_to_quarantine(tmp_path, monkeypatch):
    hourly = good_hourly()
    add_hour(hourly, f"{DAY}T02:00", temperature=25.0)   # a second 02:00 with another value

    with pytest.warns(UserWarning):
        valid, quarantine = run_validate(tmp_path, monkeypatch, hourly)

    assert quarantine.count() == 2                  # both copies of 02:00
    assert valid.count() == 23


def test_three_missing_hours_exceed_the_budget(tmp_path, monkeypatch):
    hourly = {column: values[3:] for column, values in good_hourly().items()}   # drop 00, 01, 02

    with pytest.warns(UserWarning):                 # DQ-03 warns about the missing hours …
        with pytest.raises(ValueError, match="exceeded budget"):   # … and the budget stops the run
            run_validate(tmp_path, monkeypatch, hourly)


def test_humidity_150_goes_to_quarantine_with_dq07(tmp_path, monkeypatch):
    hourly = good_hourly()
    hourly["relative_humidity_2m"][5] = 150         # break it: impossible humidity at 05:00

    with pytest.warns(UserWarning):                 # 1 unusable hour, within budget
        valid, quarantine = run_validate(tmp_path, monkeypatch, hourly)

    assert quarantine.count() == 1
    assert valid.count() == 23
    assert "DQ-07" in quarantine.first()["failed_rules"]


def test_file_with_several_kinds_of_errors(tmp_path, monkeypatch):
    """One file, four different problems, all within the error budget.

    - 05:00 humidity 150 %              -> quarantine, DQ-07   (1 unusable hour)
    - 07:00 dew point above temperature -> quarantine, DQ-09   (1 unusable hour)
    - 10:00 twice, identical            -> one copy removed    (not unusable)
    - 2026-06-02 00:00, outside range   -> excluded            (not unusable)
    """
    hourly = good_hourly()
    hourly["relative_humidity_2m"][5] = 150
    hourly["dew_point_2m"][7] = 20.0                # above the 18.0 °C temperature
    add_hour(hourly, f"{DAY}T10:00")                # identical copy of 10:00
    add_hour(hourly, "2026-06-02T00:00")            # one hour after the range

    with pytest.warns(UserWarning) as record:
        valid, quarantine = run_validate(tmp_path, monkeypatch, hourly)

    # every row lands in exactly one place: 26 read = 1 excluded + 1 removed + 22 valid + 2 quarantined
    assert valid.count() == 22
    assert quarantine.count() == 2

    broken_rules = {rule for row in quarantine.collect() for rule in row["failed_rules"]}
    assert broken_rules == {"DQ-07", "DQ-09"}

    messages = " ".join(str(w.message) for w in record)
    assert "DQ-03" in messages                      # the hour outside the range was reported
    assert "DQ-04" in messages                      # the identical duplicate was reported
    assert "within budget" in messages              # 2 unusable hours = exactly the budget
