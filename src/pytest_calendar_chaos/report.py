"""Failure report text. Plain text, no ANSI codes."""

from __future__ import annotations

from datetime import timezone

from pytest_calendar_chaos.catalog import Scenario


def _quote(nodeid: str) -> str:
    return '"' + nodeid.replace("\\", "\\\\").replace('"', '\\"') + '"'


def reproduce_lines(nodeid: str, scenario: Scenario) -> list[str]:
    path = nodeid.split("::")[0]
    return [
        f"pytest {_quote(nodeid)}",
        f"pytest {path} --calendar-case {scenario.id}",
    ]


def clock_text(scenario: Scenario) -> str:
    text = scenario.moment.isoformat()
    if scenario.zone != "UTC":
        utc = scenario.moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        text += f" ({utc})"
    return text


def build_section(nodeid: str, scenario: Scenario, tick: bool) -> str:
    case = scenario.case
    lines = [
        f"Case:      {case.label}  [{case.preset} / {case.id}]",
        f"Zone:      {scenario.zone}",
        f"Clock:     {clock_text(scenario)}",
        f"Frozen:    {'no (tick=True)' if tick else 'yes (tick=False)'}",
    ]
    if scenario.note:
        lines.insert(3, f"Transition: {scenario.note}")
    repro = reproduce_lines(nodeid, scenario)
    lines.append(f"Reproduce: {repro[0]}")
    lines.extend(f"           {line}" for line in repro[1:])
    return "\n".join(lines)
