import pytest


def test_dst_preset_freezes_exact_moments(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from datetime import datetime, timezone
        import pytest

        @pytest.mark.calendar_chaos(cases=["dst"], zones=["America/New_York", "Europe/London"])
        def test_a(calendar_case):
            assert datetime.now(timezone.utc) == calendar_case.moment.astimezone(timezone.utc)
            assert calendar_case.case.preset == "dst"
        """
    )
    pytester.runpytest().assert_outcomes(passed=12)


def test_dst_ids_in_collection(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["dst"], zones=["UTC", "America/New_York"])
        def test_a(): pass
        """
    )
    out = pytester.runpytest("--collect-only", "-q").stdout.str()
    assert "test_a[dst-fall-second-repeat-2027@america-new-york]" in out
    assert "@utc" not in out


def test_dst_failure_report_has_transition_line(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        test_x="""
        import pytest
        @pytest.mark.calendar_chaos(cases=["dst"], zones=["America/New_York"])
        def test_a(calendar_case):
            assert calendar_case.case.id != "dst-spring-before-2027"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=5, failed=1)
    result.stdout.fnmatch_lines(
        [
            "Case:*[[]dst / dst-spring-before-2027[]]",
            "Zone:      America/New_York",
            "Clock:     2027-03-14T01:59:00-05:00 (2027-03-14T06:59:00Z)",
            "Transition: 2027-03-14 02:00 local clocks jump to 03:00 (America/New_York)",
            "Frozen:*",
        ]
    )


def test_dst_without_dst_zone_is_collection_error(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["dst"], zones=["Asia/Tokyo"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(['*"dst" requested but none of zones*Asia/Tokyo*'])


def test_calendar_case_filter_works_for_dst(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["dst"], zones=["America/New_York", "Europe/London"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest("--calendar-case", "dst-fall-second-repeat-2027")
    result.assert_outcomes(passed=2)
    result = pytester.runpytest("--calendar-case", "dst-fall-second-repeat-2027@europe-london")
    result.assert_outcomes(passed=1)
