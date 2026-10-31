import re
import sys

import pytest

from pytest_calendar_chaos import report

FAILING = """
import pytest

@pytest.mark.calendar_chaos(cases=["month_end"], zones=["UTC", "America/New_York"])
def test_renewal(calendar_case):
    assert calendar_case.case.id != "month-end-jan-31-2027"
"""


def test_failure_section_contents(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(test_billing=FAILING)
    result = pytester.runpytest()
    result.assert_outcomes(passed=8, failed=2)
    result.stdout.fnmatch_lines(
        [
            "*Calendar chaos*",
            "Case:      31-day month end  [[]month_end / month-end-jan-31-2027[]]",
            "Zone:      UTC",
            "Clock:     2027-01-31T12:00:00+00:00",
            "Frozen:    yes (tick=False)",
        ]
    )
    nodeid = "test_billing.py::test_renewal[month-end-jan-31-2027]"
    out = result.stdout.str()
    assert f"Reproduce: pytest {report.quote_arg(nodeid)}" in out
    assert "pytest test_billing.py --calendar-case month-end-jan-31-2027" in out
    result.stdout.fnmatch_lines(
        [
            "Zone:      America/New_York",
            "Clock:     2027-01-31T12:00:00-05:00 (2027-01-31T17:00:00Z)",
        ]
    )


def test_passing_has_no_section(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["midnight"])
        def test_ok(): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=2)
    assert "Calendar chaos" not in result.stdout.str()
    assert "calendar chaos failures" not in result.stdout.str()


def test_setup_failure_gets_section(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def boom():
            raise RuntimeError("setup blew up")

        @pytest.mark.calendar_chaos(cases=["midnight"])
        def test_a(boom): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=2)
    result.stdout.fnmatch_lines(["*Calendar chaos*", "Case:*", "Reproduce:*"])


def test_terminal_summary_lists_each_failure(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(test_billing=FAILING)
    out = pytester.runpytest().stdout.str()
    assert "calendar chaos failures" in out
    summary = out.split("calendar chaos failures", 1)[1]
    assert "test_billing.py::test_renewal[month-end-jan-31-2027]" in summary
    assert "test_billing.py::test_renewal[month-end-jan-31-2027@america-new-york]" in summary


def test_reproduce_round_trip(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(test_billing=FAILING)
    out = pytester.runpytest().stdout.str()
    nodeid = re.search(r"Reproduce: pytest (\S+)", out)
    assert nodeid is not None
    rerun = pytester.runpytest(nodeid.group(1).strip("'\""))
    rerun.assert_outcomes(failed=1)

    by_id = pytester.runpytest("test_billing.py", "--calendar-case", "month-end-jan-31-2027")
    by_id.assert_outcomes(failed=2)  # base ID matches both zones


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell quoting")
def test_reproduce_lines_are_safe_to_paste_into_a_posix_shell() -> None:
    import shlex

    from pytest_calendar_chaos import catalog, report

    scenario = catalog.expand(["leap_day"])[0]
    nodeid = "dir with space/test_x.py::test_a[$(touch pwned)`id`\"'q]"
    lines = report.reproduce_lines(nodeid, scenario)
    # shlex round trip proves each is one literal argument, with no expansion left to the shell.
    assert shlex.split(lines[0]) == ["pytest", nodeid]
    assert shlex.split(lines[1]) == [
        "pytest",
        "dir with space/test_x.py",
        "--calendar-case",
        scenario.id,
    ]


def test_reproduce_lines_use_windows_quoting_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    from pytest_calendar_chaos import catalog, report

    monkeypatch.setattr(report, "_WINDOWS", True)
    scenario = catalog.expand(["leap_day"])[0]
    assert (
        report.reproduce_lines("a b/test_x.py::t[1]", scenario)[0] == 'pytest "a b/test_x.py::t[1]"'
    )
