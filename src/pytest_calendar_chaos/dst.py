"""DST scenarios, computed per zone from zoneinfo. No pytest imports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import cache
from typing import NamedTuple
from zoneinfo import ZoneInfo

from pytest_calendar_chaos.catalog import Case, Scenario, validate_zone

REFERENCE_YEAR = 2027
_HOUR = 3600


class Transition(NamedTuple):
    instant_utc: datetime
    offset_before: timedelta
    offset_after: timedelta

    @property
    def is_spring(self) -> bool:
        """Clocks go forward: a gap of local times that never happen."""
        return self.offset_after > self.offset_before


def _offset(info: ZoneInfo, ts: int) -> timedelta:
    off = datetime.fromtimestamp(ts, info).utcoffset()
    if off is None:  # pragma: no cover - ZoneInfo always yields an offset
        raise RuntimeError(f"no UTC offset for {info.key} at {ts}")
    return off


def transitions(zone: str, year: int = REFERENCE_YEAR) -> list[Transition]:
    """UTC offset changes in ``year``, found hourly then bisected to the second.

    Assumes at most one change per hour, which holds for every zone in tzdata.
    """
    return list(_transitions(zone, year))


@cache
def _transitions(zone: str, year: int) -> tuple[Transition, ...]:
    # Cached: the hourly scan is the slow part and the result is immutable. The cache lives for
    # the process, which is fine because tz data does not change under a running pytest session.
    info = validate_zone(zone)
    start = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    found: list[Transition] = []
    prev_ts, prev_off = start, _offset(info, start)
    for ts in range(start + _HOUR, end + 1, _HOUR):
        off = _offset(info, ts)
        if off != prev_off:
            lo, hi = prev_ts, ts  # offset(lo) == prev_off, offset(hi) != prev_off
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if _offset(info, mid) == prev_off:
                    lo = mid
                else:
                    hi = mid
            found.append(Transition(datetime.fromtimestamp(hi, timezone.utc), prev_off, off))
            prev_off = off
        prev_ts = ts
    return tuple(found)


def _describe(t: Transition, zone: str) -> str:
    before = t.instant_utc + t.offset_before
    after = t.instant_utc + t.offset_after
    verb = "jump to" if t.is_spring else "go back to"
    return f"{before:%Y-%m-%d %H:%M} local clocks {verb} {after:%H:%M} ({zone})"


def scenarios(zone: str, year: int = REFERENCE_YEAR) -> list[Scenario]:
    """Scenarios for every transition of ``zone`` in ``year``, in time order."""
    info = validate_zone(zone)
    found = transitions(zone, year)
    totals = {
        "spring": sum(t.is_spring for t in found),
        "fall": sum(not t.is_spring for t in found),
    }
    seen = {"spring": 0, "fall": 0}
    out: list[Scenario] = []
    for t in found:
        kind = "spring" if t.is_spring else "fall"
        seen[kind] += 1
        number = f"-{seen[kind]}" if totals[kind] > 1 else ""
        ts = int(t.instant_utc.timestamp())
        if t.is_spring:
            specs = [
                ("before", "1 minute before the gap", -60),
                ("at", "the exact instant the clocks jump", 0),
                ("after", "1 minute after the gap", 60),
            ]
            label_prefix = "Spring forward"
        else:
            repeat = int((t.offset_before - t.offset_after).total_seconds())
            specs = [
                ("before", "1 minute before the repeated time", -60),
                ("at", "the exact instant the clocks go back", 0),
                ("first-repeat", "first pass through the repeated time", -repeat // 2),
                ("second-repeat", "second pass through the repeated time", repeat // 2),
                ("after", "1 minute after the repeated time", repeat + 60),
            ]
            label_prefix = "Fall back"
        note = _describe(t, zone)
        for what, desc, delta in specs:
            moment = datetime.fromtimestamp(ts + delta, info)
            case = Case(
                id=f"dst-{kind}{number}-{what}-{year}",
                label=f"{label_prefix}: {desc}",
                preset="dst",
                wall_time=moment.replace(tzinfo=None, fold=0),
            )
            out.append(Scenario(case=case, zone=zone, moment=moment, note=note))
    return out
