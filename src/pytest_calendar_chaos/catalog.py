"""Case catalog. Pure data: no pytest imports.

Case IDs are a public API. Saved reproduce commands depend on them, so never
rename or remove one without a breaking-change release.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Case:
    id: str
    label: str
    preset: str
    wall_time: datetime  # naive local wall-clock time (a UTC time when ``utc`` is True)
    utc: bool = False  # True: an absolute UTC instant, the same in every zone


@dataclass(frozen=True)
class Scenario:
    case: Case
    zone: str
    moment: datetime  # aware, tzinfo=ZoneInfo(zone)
    note: str | None = None  # e.g. DST transition description

    @property
    def id(self) -> str:
        if self.zone == "UTC":
            return self.case.id
        return f"{self.case.id}@{zone_slug(self.zone)}"


def _c(id_: str, label: str, preset: str, *args: int) -> Case:
    # args are (year, month, day[, hour, minute, second[, microsecond]])
    wall_time = datetime(*args)  # type: ignore[arg-type]
    return Case(id=id_, label=label, preset=preset, wall_time=wall_time)


def _u(id_: str, label: str, preset: str, *args: int) -> Case:
    # Like _c, but the time is a UTC instant that does not shift with the zone.
    return Case(id=id_, label=label, preset=preset, wall_time=datetime(*args), utc=True)  # type: ignore[arg-type]


_NOON = (12, 0, 0)
_LAST_US = (23, 59, 59, 999999)

PRESETS: dict[str, tuple[Case, ...]] = {
    "leap_day": (
        _c("leap-eve-2028", "Day before leap day", "leap_day", 2028, 2, 28, *_NOON),
        _c("leap-day-2028", "Leap day", "leap_day", 2028, 2, 29, *_NOON),
        _c(
            "leap-day-last-microsecond-2028",
            "Last microsecond of leap day",
            "leap_day",
            2028,
            2,
            29,
            *_LAST_US,
        ),
        _c("leap-day-after-2028", "Day after leap day", "leap_day", 2028, 3, 1, *_NOON),
    ),
    "month_end": (
        _c("month-end-jan-31-2027", "31-day month end", "month_end", 2027, 1, 31, *_NOON),
        _c(
            "month-end-feb-28-2027",
            "February end, non-leap year",
            "month_end",
            2027,
            2,
            28,
            *_NOON,
        ),
        _c(
            "month-start-mar-01-2027",
            "First day after February",
            "month_end",
            2027,
            3,
            1,
            *_NOON,
        ),
        _c("month-end-apr-30-2027", "30-day month end", "month_end", 2027, 4, 30, *_NOON),
        _c(
            "month-end-feb-29-2028",
            "February end, leap year",
            "month_end",
            2028,
            2,
            29,
            *_NOON,
        ),
    ),
    "year_end": (
        _c("year-end-2027", "Last day of year", "year_end", 2027, 12, 31, *_NOON),
        _c(
            "year-end-last-microsecond-2027",
            "Last microsecond of year",
            "year_end",
            2027,
            12,
            31,
            *_LAST_US,
        ),
        _c("new-year-2028", "First instant of new year", "year_end", 2028, 1, 1, 0, 0, 0),
    ),
    "midnight": (
        _c(
            "midnight-before-2027-06-15",
            "Last microsecond before midnight",
            "midnight",
            2027,
            6,
            15,
            *_LAST_US,
        ),
        _c(
            "midnight-after-2027-06-16",
            "Exactly midnight",
            "midnight",
            2027,
            6,
            16,
            0,
            0,
            0,
        ),
    ),
    # 2026 has 53 ISO weeks, so the calendar year and the ISO year disagree around New Year.
    "iso_week": (
        _c(
            "iso-week-53-2026-12-31",
            "Last day of 2026, ISO week 53",
            "iso_week",
            2026,
            12,
            31,
            *_NOON,
        ),
        _c(
            "iso-week-53-new-year-2027",
            "New Year's Day 2027, still ISO week 53 of 2026",
            "iso_week",
            2027,
            1,
            1,
            *_NOON,
        ),
        _c(
            "iso-week-1-2027-01-04",
            "First day of ISO week 1 of 2027",
            "iso_week",
            2027,
            1,
            4,
            *_NOON,
        ),
        # 2020 is a leap year that starts on a Wednesday, so it also has 53 ISO weeks.
        _c(
            "iso-week-53-leap-2020-12-31",
            "Last day of leap year 2020, ISO week 53",
            "iso_week",
            2020,
            12,
            31,
            *_NOON,
        ),
        _c(
            "iso-week-53-new-year-2021",
            "New Year's Day 2021, still ISO week 53 of 2020",
            "iso_week",
            2021,
            1,
            1,
            *_NOON,
        ),
    ),
    # Century years: 2000 is a leap year (divisible by 400), 2100 is not (divisible by 100 only).
    "century": (
        _c(
            "century-leap-2000-02-29",
            "Leap day 2000 (century leap year)",
            "century",
            2000,
            2,
            29,
            *_NOON,
        ),
        _c(
            "century-2100-02-28",
            "Last day of February 2100 (not a leap year)",
            "century",
            2100,
            2,
            28,
            *_NOON,
        ),
        _c(
            "century-2100-03-01",
            "March 1, 2100, the day after Feb 28",
            "century",
            2100,
            3,
            1,
            *_NOON,
        ),
        _c(
            "century-2100-02-28-last-microsecond",
            "Last microsecond of February 2100",
            "century",
            2100,
            2,
            28,
            *_LAST_US,
        ),
    ),
    # A signed 32-bit time_t overflows after 2038-01-19 03:14:07 UTC (2**31 - 1 seconds).
    "y2038": (
        _u(
            "y2038-before-limit",
            "One second before the 32-bit time_t limit",
            "y2038",
            2038,
            1,
            19,
            3,
            14,
            6,
        ),
        _u(
            "y2038-last-valid-second",
            "Last second a signed 32-bit time_t can hold",
            "y2038",
            2038,
            1,
            19,
            3,
            14,
            7,
        ),
        _u(
            "y2038-after-limit",
            "First second past the 32-bit time_t limit",
            "y2038",
            2038,
            1,
            19,
            3,
            14,
            8,
        ),
    ),
}


DST_PRESET = "dst"


def preset_names() -> list[str]:
    """All valid preset names, sorted (includes the computed ``dst`` preset)."""
    return sorted([*PRESETS, DST_PRESET])


def catalog_lines() -> list[str]:
    """Human-readable catalog, as printed by ``--calendar-chaos-list``."""
    lines: list[str] = []
    for preset, cases in PRESETS.items():
        lines.append(f"{preset}:")
        for case in cases:
            when = case.wall_time.isoformat(sep=" ") + (" UTC" if case.utc else "")
            lines.append(f"  {case.id:<32} {when:<30}  {case.label}")
    lines.append(f"{DST_PRESET}:")
    lines.append("  computed per zone from zoneinfo for 2027: spring-forward and fall-back moments")
    return lines


def zone_slug(zone: str) -> str:
    return zone.lower().replace("/", "-").replace("_", "-")


def normalize_preset(name: str) -> str:
    return name.strip().lower().replace("-", "_")


def validate_zone(zone: str) -> ZoneInfo:
    try:
        return ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"unknown time zone {zone!r}") from exc


def expand(presets: Iterable[str], zones: Sequence[str] = ("UTC",)) -> list[Scenario]:
    """Expand preset names and zones into scenarios in the documented fixed order.

    Order: preset order given, then catalog order, then zone order (the ``dst``
    preset is ordered zone, then transition time, then kind). A scenario is
    dropped only when the same scenario ID has already been produced.
    """
    from pytest_calendar_chaos import dst  # lazy: dst imports this module

    zone_list = list(dict.fromkeys(zones))
    infos = [(z, validate_zone(z)) for z in zone_list]
    seen_ids: set[str] = set()
    scenarios: list[Scenario] = []

    def add(scenario: Scenario) -> None:
        if scenario.id not in seen_ids:
            seen_ids.add(scenario.id)
            scenarios.append(scenario)

    for raw in presets:
        name = normalize_preset(raw)
        if name == DST_PRESET:
            dst_scenarios = [s for z in zone_list for s in dst.scenarios(z)]
            if not dst_scenarios:
                raise ValueError(
                    f'"dst" requested but none of zones {zone_list} '
                    f"observe DST in {dst.REFERENCE_YEAR}"
                )
            for scenario in dst_scenarios:
                add(scenario)
        elif name in PRESETS:
            for case in PRESETS[name]:
                for zone, info in infos:
                    if case.utc:
                        moment = case.wall_time.replace(tzinfo=timezone.utc).astimezone(info)
                    else:
                        moment = case.wall_time.replace(tzinfo=info)
                    add(Scenario(case=case, zone=zone, moment=moment))
        else:
            raise ValueError(f"unknown preset {raw!r}; valid presets: {', '.join(preset_names())}")
    return scenarios
