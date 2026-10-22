"""Case catalog. Pure data: no pytest imports.

Case IDs are a public API. Saved reproduce commands depend on them, so never
rename or remove one without a breaking-change release.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Case:
    id: str
    label: str
    preset: str
    wall_time: datetime  # naive local wall-clock time


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
}


DST_PRESET = "dst"


def preset_names() -> list[str]:
    """All valid preset names, sorted (includes the computed ``dst`` preset)."""
    return sorted([*PRESETS, DST_PRESET])


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
                    add(Scenario(case=case, zone=zone, moment=case.wall_time.replace(tzinfo=info)))
        else:
            raise ValueError(f"unknown preset {raw!r}; valid presets: {', '.join(preset_names())}")
    return scenarios
