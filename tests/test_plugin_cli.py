import pytest

SRC = """
import pytest

@pytest.mark.calendar_chaos(cases=["leap_day"], zones=["UTC", "America/New_York"])
def test_a(): pass

def test_unmarked(): pass
"""


def test_base_id_matches_every_zone(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(SRC)
    result = pytester.runpytest("--calendar-case", "leap-day-2028", "-v")
    result.assert_outcomes(passed=3)  # 2 zones + unmarked
    result.stdout.fnmatch_lines(
        [
            "*test_a[[]leap-day-2028[]] PASSED*",
            "*test_a[[]leap-day-2028@america-new-york[]] PASSED*",
        ]
    )


def test_full_id_runs_one(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(SRC)
    result = pytester.runpytest("--calendar-case", "leap-day-2028@america-new-york")
    result.assert_outcomes(passed=2)  # 1 scenario + unmarked


def test_repeatable(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(SRC)
    result = pytester.runpytest(
        "--calendar-case", "leap-eve-2028", "--calendar-case", "leap-day-after-2028"
    )
    result.assert_outcomes(passed=5)  # 2 ids x 2 zones + unmarked


def test_unmatched_id_warns_not_errors(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(SRC)
    result = pytester.runpytest("--calendar-case", "no-such-case")
    result.stdout.fnmatch_lines(["*WARNING: --calendar-case 'no-such-case' matched no*"])
    assert result.ret == 0
    result.assert_outcomes(passed=1, skipped=1)


def test_partial_match_warns_only_for_unmatched(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(SRC)
    result = pytester.runpytest("--calendar-case", "leap-day-2028", "--calendar-case", "nope")
    out = result.stdout.str()
    assert "'nope' matched no" in out
    assert "'leap-day-2028' matched no" not in out


def test_unmarked_still_run(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(SRC)
    result = pytester.runpytest("--calendar-case", "no-such-case", "-v")
    result.stdout.fnmatch_lines(["*test_unmarked PASSED*"])
