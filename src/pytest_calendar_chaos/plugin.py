"""pytest hooks and fixtures for pytest-calendar-chaos."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
import time_machine

from pytest_calendar_chaos import catalog, report

MARKER = "calendar_chaos"
CLOCK_FIXTURE = "_calendar_chaos_clock"
PROPERTY_KEY = "calendar_chaos_scenario"

_requested_ids: pytest.StashKey[set[str]] = pytest.StashKey()
_matched_ids: pytest.StashKey[set[str]] = pytest.StashKey()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("calendar-chaos")
    group.addoption(
        "--calendar-case",
        action="append",
        default=[],
        metavar="ID",
        help="Run only calendar_chaos scenarios with this case ID (full or base ID). Repeatable.",
    )
    group.addoption(
        "--calendar-chaos-list",
        action="store_true",
        default=False,
        help="Print the calendar_chaos case catalog and exit.",
    )
    parser.addini(
        "calendar_chaos_default_zones",
        "Default IANA time zones (space separated) for calendar_chaos markers without zones.",
        type="args",
        default=[],
    )


def pytest_cmdline_main(config: pytest.Config) -> int | None:
    if config.getoption("calendar_chaos_list"):
        # The terminal reporter is not registered yet at this point, so print directly.
        print("\n".join(catalog.catalog_lines()))
        return 0
    return None


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        'calendar_chaos(cases, zones=["UTC"], tick=False): '
        "run the test across calendar edge-case scenarios",
    )
    config.stash[_requested_ids] = set(config.getoption("--calendar-case"))
    config.stash[_matched_ids] = set()


def _marker_args(marker: pytest.Mark, default_zones: list[str]) -> tuple[list[str], list[str]]:
    cases = marker.kwargs.get("cases", marker.args[0] if marker.args else None)
    if isinstance(cases, str) or not cases:
        pytest.fail(
            f"{MARKER}: 'cases' must be a non-empty list of preset names; "
            f"valid presets: {', '.join(catalog.preset_names())}",
            pytrace=False,
        )
    zones = marker.kwargs.get("zones", default_zones)
    if isinstance(zones, str) or not zones:
        pytest.fail(f"{MARKER}: 'zones' must be a non-empty list of IANA names", pytrace=False)
    return list(cases), list(zones)


def _selected(scenario: catalog.Scenario, wanted: set[str]) -> bool:
    return scenario.id in wanted or scenario.case.id in wanted


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    marker = metafunc.definition.get_closest_marker(MARKER)
    if marker is None:
        return
    if metafunc.definition.get_closest_marker("time_machine") is not None:
        pytest.fail(
            f"{MARKER} conflicts with the time_machine marker: both control the clock. "
            "Use only one on a test.",
            pytrace=False,
        )
    default_zones = list(metafunc.config.getini("calendar_chaos_default_zones")) or ["UTC"]
    cases, zones = _marker_args(marker, default_zones)
    try:
        scenarios = catalog.expand(cases, zones)
    except ValueError as exc:
        pytest.fail(f"{MARKER}: {exc}", pytrace=False)

    wanted = metafunc.config.stash[_requested_ids]
    if wanted:
        scenarios = [s for s in scenarios if _selected(s, wanted)]
        metafunc.config.stash[_matched_ids].update(
            i for i in wanted if any(i in (s.id, s.case.id) for s in scenarios)
        )
        if not scenarios:
            # One explicitly skipped placeholder: robust against the user's
            # empty_parameter_set_mark setting, and never runs the test unfrozen.
            skip = pytest.mark.skip(reason="no calendar_chaos scenario matches --calendar-case")
            metafunc.parametrize(
                CLOCK_FIXTURE,
                [pytest.param(None, marks=skip)],
                ids=["no-matching-calendar-case"],
                indirect=True,
            )
            return

    metafunc.parametrize(CLOCK_FIXTURE, scenarios, ids=[s.id for s in scenarios], indirect=True)


@pytest.fixture(autouse=True)
def _calendar_chaos_clock(
    request: pytest.FixtureRequest,
) -> Generator[catalog.Scenario | None, None, None]:
    scenario: catalog.Scenario | None = getattr(request, "param", None)
    if scenario is None:
        yield None
        return
    marker = request.node.get_closest_marker(MARKER)
    tick = bool(marker.kwargs.get("tick", False)) if marker else False
    with time_machine.travel(scenario.moment, tick=tick):
        yield scenario


@pytest.fixture
def calendar_case(_calendar_chaos_clock: catalog.Scenario | None) -> catalog.Scenario | None:
    """The Scenario this test runs under, or None for unmarked tests."""
    return _calendar_chaos_clock


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[Any]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    rep = yield
    callspec = getattr(item, "callspec", None)
    scenario = callspec.params.get(CLOCK_FIXTURE) if callspec else None
    if scenario is not None and rep.failed:
        marker = item.get_closest_marker(MARKER)
        tick = bool(marker.kwargs.get("tick", False)) if marker else False
        rep.sections.append(("Calendar chaos", report.build_section(item.nodeid, scenario, tick)))
        rep.user_properties.append((PROPERTY_KEY, scenario.id))
    return rep


def _failed_reports(terminalreporter: Any) -> list[Any]:
    out = []
    for key in ("failed", "error"):
        for rep in terminalreporter.stats.get(key, []):
            # CollectReport (collection errors) has no user_properties.
            if any(k == PROPERTY_KEY for k, _ in getattr(rep, "user_properties", [])):
                out.append(rep)
    return out


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    failed = _failed_reports(terminalreporter)
    if failed:
        terminalreporter.section("calendar chaos failures")
        for rep in failed:
            scenario_id = dict(rep.user_properties)[PROPERTY_KEY]
            terminalreporter.write_line(f"{rep.nodeid}  [{scenario_id}]")
            terminalreporter.write_line(f'  Reproduce: pytest "{rep.nodeid}"')

    # Under xdist the controller never runs collection hooks, so it cannot know what matched.
    if getattr(config.option, "dist", "no") != "no":
        return
    requested: set[str] = config.stash[_requested_ids]
    matched: set[str] = config.stash[_matched_ids]
    for case_id in sorted(requested - matched):
        terminalreporter.write_line(
            f"WARNING: --calendar-case {case_id!r} matched no calendar_chaos scenario",
            yellow=True,
        )
