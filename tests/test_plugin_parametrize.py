import pytest


def test_unmarked_runs_once(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("def test_a(): pass")
    result = pytester.runpytest("-v")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*test_a PASSED*"])


def test_leap_day_generates_four_with_ids(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["leap_day"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest("-v")
    result.assert_outcomes(passed=4)
    result.stdout.fnmatch_lines(
        [
            "*test_a[[]leap-eve-2028[]] PASSED*",
            "*test_a[[]leap-day-2028[]] PASSED*",
            "*test_a[[]leap-day-last-microsecond-2028[]] PASSED*",
            "*test_a[[]leap-day-after-2028[]] PASSED*",
        ]
    )


def test_zone_suffix_only_non_utc(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["year_end"], zones=["UTC", "Asia/Tokyo"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest("--collect-only", "-q")
    out = result.stdout.str()
    assert "test_a[year-end-2027]" in out
    assert "test_a[year-end-2027@asia-tokyo]" in out
    assert "@utc" not in out


def test_class_and_module_markers(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        test_cls="""
        import pytest
        @pytest.mark.calendar_chaos(cases=["midnight"])
        class TestX:
            def test_a(self): pass
        """,
        test_mod="""
        import pytest
        pytestmark = pytest.mark.calendar_chaos(cases=["year_end"])
        def test_b(): pass
        """,
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=5)


def test_closest_marker_wins(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        pytestmark = pytest.mark.calendar_chaos(cases=["year_end"])
        @pytest.mark.calendar_chaos(cases=["midnight"])
        def test_a(): pass
        """
    )
    pytester.runpytest().assert_outcomes(passed=2)


def test_combines_with_parametrize(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.parametrize("n", [1, 2])
        @pytest.mark.calendar_chaos(cases=["midnight"])
        def test_a(n): pass
        """
    )
    result = pytester.runpytest("--collect-only", "-q")
    ids = [ln for ln in result.stdout.lines if "::test_a[" in ln]
    assert len(ids) == 4
    assert any("midnight-before-2027-06-15" in i and "1" in i for i in ids)


def test_unknown_preset_error(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["bogus"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*unknown preset 'bogus'*valid presets: century, dst, iso_week, leap_day*"]
    )


def test_unknown_zone_error(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["leap_day"], zones=["Mars/Olympus"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*Mars/Olympus*"])


def test_empty_cases_error(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=[])
        def test_a(): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*non-empty list*"])


def test_conflict_with_time_machine_marker(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.time_machine("2020-01-01")
        @pytest.mark.calendar_chaos(cases=["leap_day"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*conflicts with the time_machine marker*"])


@pytest.mark.parametrize(
    ("marker", "message"),
    [
        (
            'calendar_chaos(cases=["leap_day"], zone=["Asia/Tokyo"])',
            "unknown argument 'zone'*did you mean 'zones'",
        ),
        ("calendar_chaos(cases=[123])", "'cases' must contain only strings"),
        ('calendar_chaos(cases=["leap_day"], zones=[1])', "'zones' must contain only strings"),
        ('calendar_chaos(cases=["leap_day"], tick="yes")', "'tick' must be True or False"),
        ('calendar_chaos(["leap_day"], ["UTC"])', "at most one positional argument"),
        ('calendar_chaos(["leap_day"], cases=["leap_day"])', "both positionally and by name"),
        ("calendar_chaos(cases=5)", "'cases' must be a non-empty list"),
    ],
)
def test_malformed_marker_arguments_fail_loudly(
    pytester: pytest.Pytester, marker: str, message: str
) -> None:
    pytester.makepyfile(
        f"""
        import pytest

        @pytest.mark.{marker}
        def test_it():
            pass
        """
    )
    result = pytester.runpytest()
    result.stdout.fnmatch_lines([f"*calendar_chaos: *{message}*"])
    assert result.ret != 0
