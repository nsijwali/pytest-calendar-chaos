import calendar
import re
from datetime import timedelta

import pytest

from pytest_calendar_chaos.catalog import PRESETS, expand, zone_slug

ALL_CASES = [c for cases in PRESETS.values() for c in cases]


def test_ids_unique_and_well_formed() -> None:
    ids = [c.id for c in ALL_CASES]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z0-9-]+", i) for i in ids)


def test_catalog_size() -> None:
    assert {k: len(v) for k, v in PRESETS.items()} == {
        "leap_day": 4,
        "month_end": 5,
        "year_end": 3,
        "midnight": 2,
    }


def test_leap_day_cases_are_in_leap_years() -> None:
    for c in PRESETS["leap_day"]:
        if "eve" in c.id or "after" in c.id or "day" in c.id:
            assert calendar.isleap(c.wall_time.year)
    assert any(c.wall_time.month == 2 and c.wall_time.day == 29 for c in PRESETS["leap_day"])


def test_month_end_and_start_cases() -> None:
    for c in PRESETS["month_end"]:
        t = c.wall_time
        if c.id.startswith("month-end-"):
            assert t.day == calendar.monthrange(t.year, t.month)[1]
        if c.id.startswith("month-start-"):
            assert t.day == 1


def test_last_microsecond_crosses_boundary() -> None:
    cases = [
        c for c in ALL_CASES if "last-microsecond" in c.id or c.id == "midnight-before-2027-06-15"
    ]
    assert len(cases) == 3
    for c in cases:
        assert (c.wall_time + timedelta(microseconds=1)).date() > c.wall_time.date()


def test_expand_order_and_dedupe() -> None:
    scenarios = expand(["leap_day", "month_end", "leap-day"], ["UTC"])
    ids = [s.id for s in scenarios]
    assert ids[:4] == [
        "leap-eve-2028",
        "leap-day-2028",
        "leap-day-last-microsecond-2028",
        "leap-day-after-2028",
    ]
    assert len(ids) == 9  # duplicate preset ignored
    # same moment, different IDs: both kept
    assert "leap-day-2028" in ids and "month-end-feb-29-2028" in ids


def test_expand_zone_suffix_and_order() -> None:
    scenarios = expand(["midnight"], ["UTC", "America/New_York"])
    assert [s.id for s in scenarios] == [
        "midnight-before-2027-06-15",
        "midnight-before-2027-06-15@america-new-york",
        "midnight-after-2027-06-16",
        "midnight-after-2027-06-16@america-new-york",
    ]
    ny = scenarios[1]
    assert ny.moment.tzinfo is not None
    assert ny.moment.utcoffset() == timedelta(hours=-4)


def test_zone_slug() -> None:
    assert zone_slug("America/New_York") == "america-new-york"


def test_expand_unknown_preset_lists_valid() -> None:
    with pytest.raises(
        ValueError, match="valid presets: dst, leap_day, midnight, month_end, year_end"
    ):
        expand(["nope"])


def test_expand_unknown_zone_names_it() -> None:
    with pytest.raises(ValueError, match="Mars/Olympus"):
        expand(["leap_day"], ["Mars/Olympus"])
