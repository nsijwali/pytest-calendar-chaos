import re

import pytest

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
            'Reproduce: pytest "test_billing.py::test_renewal[[]month-end-jan-31-2027[]]"',
            "           pytest test_billing.py --calendar-case month-end-jan-31-2027",
        ]
    )
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
    nodeid = re.search(r'Reproduce: pytest "([^"]+)"', out)
    assert nodeid is not None
    rerun = pytester.runpytest(nodeid.group(1))
    rerun.assert_outcomes(failed=1)

    by_id = pytester.runpytest("test_billing.py", "--calendar-case", "month-end-jan-31-2027")
    by_id.assert_outcomes(failed=2)  # base ID matches both zones
