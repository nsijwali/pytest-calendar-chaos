import sys

import pytest


def test_mocked_moment_everywhere(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import time
        from datetime import date, datetime, timezone
        import pytest

        @pytest.mark.calendar_chaos(cases=["leap_day"])
        def test_a(calendar_case):
            m = calendar_case.moment
            assert datetime.now(timezone.utc) == m
            assert date.today() == m.date()
            assert time.time() == m.timestamp()
            assert datetime.now(timezone.utc) == datetime.now(timezone.utc)  # frozen
        """
    )
    pytester.runpytest().assert_outcomes(passed=4)


def test_microsecond_precision_is_exact(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from datetime import datetime, timezone
        import pytest

        @pytest.mark.calendar_chaos(cases=["leap_day", "year_end", "midnight"])
        def test_a(calendar_case):
            assert datetime.now(timezone.utc) == calendar_case.moment.astimezone(timezone.utc)
            assert datetime.now(timezone.utc).microsecond == calendar_case.moment.microsecond
        """
    )
    pytester.runpytest().assert_outcomes(passed=9)


@pytest.mark.skipif(sys.platform == "win32", reason="time.tzset unavailable on Windows")
def test_non_utc_zone_naive_now_is_local_wall_time(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from datetime import datetime
        import pytest

        @pytest.mark.calendar_chaos(cases=["leap_day"], zones=["America/New_York", "Asia/Kolkata"])
        def test_a(calendar_case):
            assert datetime.now() == calendar_case.case.wall_time
        """
    )
    pytester.runpytest().assert_outcomes(passed=8)


def test_scoped_fixtures_and_restore(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from datetime import datetime, timezone
        import pytest

        @pytest.fixture
        def func_now():
            return datetime.now(timezone.utc)

        @pytest.fixture(scope="module")
        def module_now():
            return datetime.now(timezone.utc)

        @pytest.mark.calendar_chaos(cases=["year_end"])
        def test_a(calendar_case, func_now, module_now):
            assert func_now == calendar_case.moment          # function scope sees the freeze
            assert module_now.year >= 2026 and module_now != calendar_case.moment  # real time

        def test_clock_restored():
            assert datetime.now(timezone.utc).year >= 2026
            assert datetime.now(timezone.utc).year != 2027 or datetime.now(timezone.utc).month != 12
        """
    )
    pytester.runpytest().assert_outcomes(passed=4)


def test_tick_true_advances(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import time
        import pytest

        @pytest.mark.calendar_chaos(cases=["midnight"], tick=True)
        def test_a():
            a = time.time()
            time.sleep(0.01)
            assert time.time() > a
        """
    )
    pytester.runpytest().assert_outcomes(passed=2)


def test_calendar_case_none_for_unmarked(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        def test_a(calendar_case):
            assert calendar_case is None
        """
    )
    pytester.runpytest().assert_outcomes(passed=1)


def test_y2038_instants_are_exact_in_any_zone(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import time
        from datetime import datetime, timezone
        import pytest

        LIMIT = 2**31 - 1

        @pytest.mark.calendar_chaos(cases=["y2038"], zones=["UTC", "America/New_York"])
        def test_a(calendar_case):
            offset = {"y2038-before-limit": -1, "y2038-last-valid-second": 0,
                      "y2038-after-limit": 1}[calendar_case.case.id]
            assert int(time.time()) == LIMIT + offset
            assert datetime.now(timezone.utc).timestamp() == LIMIT + offset
        """
    )
    pytester.runpytest().assert_outcomes(passed=6)


def test_iso_week_53_is_visible_to_the_code_under_test(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from datetime import datetime
        import pytest

        @pytest.mark.calendar_chaos(cases=["iso_week"])
        def test_a(calendar_case):
            now = datetime.now()
            iso_year, iso_week, _ = now.isocalendar()
            if calendar_case.case.id == "iso-week-53-new-year-2027":
                assert now.year == 2027 and (iso_year, iso_week) == (2026, 53)
            elif calendar_case.case.id == "iso-week-53-2026-12-31":
                assert (iso_year, iso_week) == (2026, 53)
            else:
                assert (iso_year, iso_week) == (2027, 1)
        """
    )
    pytester.runpytest().assert_outcomes(passed=3)
