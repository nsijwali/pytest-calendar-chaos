import pytest

from pytest_calendar_chaos import catalog


def test_list_prints_catalog_and_exits(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        def test_should_not_run():
            raise AssertionError("tests must not run with --calendar-chaos-list")
        """
    )
    result = pytester.runpytest("--calendar-chaos-list")
    assert result.ret == 0
    out = result.stdout.str()
    for preset, cases in catalog.PRESETS.items():
        assert f"{preset}:" in out
        for case in cases:
            assert case.id in out
    assert "dst:" in out
    assert "2028-02-29 23:59:59.999999" in out
    assert "collected" not in out


def test_catalog_lines_cover_every_case() -> None:
    text = "\n".join(catalog.catalog_lines())
    for cases in catalog.PRESETS.values():
        for case in cases:
            assert case.id in text and case.label in text


def test_default_zones_ini_applies_without_zones(pytester: pytest.Pytester) -> None:
    pytester.makeini("[pytest]\ncalendar_chaos_default_zones = UTC America/New_York\n")
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["midnight"])
        def test_a(): pass
        """
    )
    out = pytester.runpytest("--collect-only", "-q").stdout.str()
    assert "test_a[midnight-after-2027-06-16]" in out
    assert "test_a[midnight-after-2027-06-16@america-new-york]" in out


def test_explicit_zones_override_ini(pytester: pytest.Pytester) -> None:
    pytester.makeini("[pytest]\ncalendar_chaos_default_zones = America/New_York\n")
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["midnight"], zones=["Asia/Tokyo"])
        def test_a(): pass
        """
    )
    out = pytester.runpytest("--collect-only", "-q").stdout.str()
    assert "@asia-tokyo" in out
    assert "@america-new-york" not in out


def test_no_ini_defaults_to_utc(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["midnight"])
        def test_a(): pass
        """
    )
    out = pytester.runpytest("--collect-only", "-q").stdout.str()
    assert "test_a[midnight-after-2027-06-16]" in out
    assert "@" not in out.split("test_a[", 1)[1].split("]", 1)[0]


def test_bad_zone_in_ini_names_the_zone(pytester: pytest.Pytester) -> None:
    pytester.makeini("[pytest]\ncalendar_chaos_default_zones = Mars/Olympus\n")
    pytester.makepyfile(
        """
        import pytest
        @pytest.mark.calendar_chaos(cases=["midnight"])
        def test_a(): pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*Mars/Olympus*"])
