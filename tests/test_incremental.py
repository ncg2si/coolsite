from datetime import date, datetime

import pytest

from incremental import fetch_window, split_by_year


def test_fetch_window_first_incremental_run():
    """Berlin after backfill: watermark 2025-12-31 23:00, run on 16 Nov 2026."""
    start, end = fetch_window(datetime(2025, 12, 31, 23, 0), date(2026, 11, 16))
    assert start == date(2025, 12, 24)  # watermark − 7 days (lookback)
    assert end == date(2026, 11, 9)  # today − 7 days (ERA5-Land delay)


def test_fetch_window_new_city_starts_1961():
    start, _ = fetch_window(None, date(2026, 11, 16))
    assert start == date(1961, 1, 1)


def test_fetch_window_crosses_year_boundary():
    """Run on 3 Jan 2027: end falls back into December 2026."""
    start, end = fetch_window(datetime(2026, 12, 26, 23, 0), date(2027, 1, 3))
    assert start == date(2026, 12, 19)
    assert end == date(2026, 12, 27)


@pytest.mark.parametrize(
    "start, end, expected",
    [
        # inside one year → 1 chunk
        (
            date(2026, 11, 4),
            date(2026, 11, 12),
            [(date(2026, 11, 4), date(2026, 11, 12))],
        ),
        # crosses 1 January → 2 chunks
        (
            date(2025, 12, 24),
            date(2026, 11, 11),
            [
                (date(2025, 12, 24), date(2025, 12, 31)),
                (date(2026, 1, 1), date(2026, 11, 11)),
            ],
        ),
        # several years → one chunk per year, last one partial
        (
            date(1961, 1, 1),
            date(1963, 6, 30),
            [
                (date(1961, 1, 1), date(1961, 12, 31)),
                (date(1962, 1, 1), date(1962, 12, 31)),
                (date(1963, 1, 1), date(1963, 6, 30)),
            ],
        ),
        # single day
        (
            date(2026, 12, 31),
            date(2026, 12, 31),
            [(date(2026, 12, 31), date(2026, 12, 31))],
        ),
        # nothing to fetch (start after end) → empty list
        (date(2026, 11, 12), date(2026, 11, 11), []),
    ],
)
def test_split_by_year(start, end, expected):
    assert split_by_year(start, end) == expected


def test_chunks_never_cross_a_year():
    """Every chunk starts and ends in the same year, and chunks follow each other without gaps."""
    chunks = split_by_year(date(1961, 1, 1), date(2026, 11, 11))
    assert len(chunks) == 66  # 1961 … 2026
    for s, e in chunks:
        assert s.year == e.year
    for (_, prev_end), (next_start, _) in zip(chunks, chunks[1:]):
        assert (next_start - prev_end).days == 1


# ---------- both together ----------


def test_no_2027_chunk_on_3_january():
    """ERA5-Land is ~7 days late: on 3 Jan 2027 there is no 2027 data to fetch yet."""
    start, end = fetch_window(datetime(2026, 12, 26, 23, 0), date(2027, 1, 3))
    chunks = split_by_year(start, end)
    assert all(e.year == 2026 for _, e in chunks)


def test_first_2027_chunk_on_8_january():
    """8 Jan - 7 days = 1 Jan → the first 2027 chunk appears."""
    start, end = fetch_window(datetime(2026, 12, 31, 23, 0), date(2027, 1, 8))
    chunks = split_by_year(start, end)
    assert chunks[-1] == (date(2027, 1, 1), date(2027, 1, 1))
