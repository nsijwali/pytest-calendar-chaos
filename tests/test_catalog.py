import calendar
import re
from datetime import datetime, timedelta, timezone

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
        "iso_week": 3,
        "y2038": 3,
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
        ValueError,
        match="valid presets: dst, iso_week, leap_day, midnight, month_end, y2038, year_end",
    ):
        expand(["nope"])


def test_expand_unknown_zone_names_it() -> None:
    with pytest.raises(ValueError, match="Mars/Olympus"):
        expand(["leap_day"], ["Mars/Olympus"])


def test_iso_week_cases_straddle_the_calendar_and_iso_year() -> None:
    by_id = {c.id: c.wall_time.isocalendar() for c in PRESETS["iso_week"]}
    # 2026 has 53 ISO weeks: Dec 31 2026 and Jan 1 2027 both belong to ISO year 2026, week 53
    assert by_id["iso-week-53-2026-12-31"][:2] == (2026, 53)
    assert by_id["iso-week-53-new-year-2027"][:2] == (2026, 53)
    assert PRESETS["iso_week"][1].wall_time.year == 2027  # calendar year already rolled over
    # the first Monday of 2027 starts ISO week 1
    assert by_id["iso-week-1-2027-01-04"][:2] == (2027, 1)
    assert by_id["iso-week-1-2027-01-04"][2] == 1


def test_y2038_cases_sit_on_the_32_bit_time_t_limit() -> None:
    limit = 2**31 - 1
    cases = {c.id: c for c in PRESETS["y2038"]}
    assert all(c.utc for c in cases.values())

    def ts(case_id: str) -> int:
        return int(cases[case_id].wall_time.replace(tzinfo=timezone.utc).timestamp())

    assert ts("y2038-before-limit") == limit - 1
    assert ts("y2038-last-valid-second") == limit
    assert ts("y2038-after-limit") == limit + 1


def test_utc_cases_keep_the_same_instant_in_every_zone() -> None:
    scenarios = expand(["y2038"], ["UTC", "America/New_York", "Asia/Kolkata"])
    assert len(scenarios) == 9
    for s in scenarios:
        assert s.moment.astimezone(timezone.utc).replace(tzinfo=None) == s.case.wall_time
    ny = next(s for s in scenarios if s.id == "y2038-last-valid-second@america-new-york")
    assert ny.moment == datetime(2038, 1, 18, 22, 14, 7, tzinfo=ny.moment.tzinfo)  # UTC-5 in winter
    assert ny.moment.timestamp() == 2**31 - 1


def test_local_cases_still_follow_the_zone() -> None:
    (s,) = [s for s in expand(["leap_day"], ["Asia/Kolkata"]) if s.case.id == "leap-day-2028"]
    assert s.moment.hour == 12 and s.moment.astimezone(timezone.utc).hour == 6
