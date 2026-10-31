"""Failure report text. Plain text, no ANSI codes."""

from __future__ import annotations

import shlex
import subprocess
import sys
from datetime import timezone

from pytest_calendar_chaos.catalog import Scenario

_WINDOWS = sys.platform == "win32"


def quote_arg(text: str) -> str:
    """Quote ``text`` as one literal argument for the user's shell.

    POSIX shells expand ``$(...)``, backticks and ``$VAR`` inside double quotes, so use
    single-quote quoting there. ``shlex`` does not apply to ``cmd.exe``, so use the Windows rules.
    """
    if _WINDOWS:
        return subprocess.list2cmdline([text])
    return shlex.quote(text)


def reproduce_lines(nodeid: str, scenario: Scenario) -> list[str]:
    path = nodeid.split("::")[0]
    return [
        f"pytest {quote_arg(nodeid)}",
        f"pytest {quote_arg(path)} --calendar-case {quote_arg(scenario.id)}",
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
