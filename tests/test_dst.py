from datetime import datetime, timedelta, timezone

import pytest

from pytest_calendar_chaos import catalog, dst

UTC = timezone.utc


def _utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)  # type: ignore[arg-type]


def test_new_york_transitions_to_the_second() -> None:
    spring, fall = dst.transitions("America/New_York", 2027)
    assert spring.instant_utc == _utc(2027, 3, 14, 7, 0, 0)
    assert fall.instant_utc == _utc(2027, 11, 7, 6, 0, 0)
    assert spring.is_spring and not fall.is_spring
    assert (spring.offset_before, spring.offset_after) == (timedelta(hours=-5), timedelta(hours=-4))
    assert (fall.offset_before, fall.offset_after) == (timedelta(hours=-4), timedelta(hours=-5))


def test_london_transitions_to_the_second() -> None:
    spring, fall = dst.transitions("Europe/London", 2027)
    assert spring.instant_utc == _utc(2027, 3, 28, 1, 0, 0)
    assert fall.instant_utc == _utc(2027, 10, 31, 1, 0, 0)


@pytest.mark.parametrize("zone", ["UTC", "Asia/Tokyo", "Asia/Kolkata", "America/Sao_Paulo"])
def test_zones_without_dst_have_no_transitions(zone: str) -> None:
    assert dst.transitions(zone, 2027) == []
    assert dst.scenarios(zone) == []


def test_southern_hemisphere_order_and_kind() -> None:
    first, second = dst.transitions("Australia/Sydney", 2027)
    assert not first.is_spring  # DST ends in April
    assert second.is_spring  # DST starts in October
    assert first.instant_utc < second.instant_utc


def test_new_york_scenarios_ids_order_and_folds() -> None:
    found = dst.scenarios("America/New_York")
    assert [s.id for s in found] == [
        "dst-spring-before-2027@america-new-york",
        "dst-spring-at-2027@america-new-york",
        "dst-spring-after-2027@america-new-york",
        "dst-fall-before-2027@america-new-york",
        "dst-fall-at-2027@america-new-york",
        "dst-fall-first-repeat-2027@america-new-york",
        "dst-fall-second-repeat-2027@america-new-york",
        "dst-fall-after-2027@america-new-york",
    ]
    by_id = {s.case.id: s for s in found}
    fall_t = _utc(2027, 11, 7, 6, 0, 0)
    first = by_id["dst-fall-first-repeat-2027"].moment
    second = by_id["dst-fall-second-repeat-2027"].moment
    assert first.fold == 0 and second.fold == 1
    assert first.astimezone(UTC) == fall_t - timedelta(minutes=30)
    assert second.astimezone(UTC) == fall_t + timedelta(minutes=30)
    # Same wall-clock time, different offsets: the repeated hour.
    assert first.replace(tzinfo=None) == second.replace(tzinfo=None, fold=0)
    assert first.utcoffset() == timedelta(hours=-4)
    assert second.utcoffset() == timedelta(hours=-5)
    assert by_id["dst-fall-after-2027"].moment.astimezone(UTC) == fall_t + timedelta(
        hours=1, minutes=1
    )
    assert by_id["dst-spring-before-2027"].moment.astimezone(UTC) == _utc(2027, 3, 14, 6, 59, 0)
    # The exact transition instant: the new offset already applies, and 02:00 is skipped.
    spring_at = by_id["dst-spring-at-2027"].moment
    assert spring_at.astimezone(UTC) == _utc(2027, 3, 14, 7, 0, 0)
    assert (spring_at.hour, spring_at.utcoffset()) == (3, timedelta(hours=-4))
    fall_at = by_id["dst-fall-at-2027"].moment
    assert fall_at.astimezone(UTC) == fall_t
    assert (fall_at.hour, fall_at.fold, fall_at.utcoffset()) == (1, 1, timedelta(hours=-5))
    assert by_id["dst-spring-after-2027"].moment.astimezone(UTC) == _utc(2027, 3, 14, 7, 1, 0)


@pytest.mark.parametrize(
    "zone", ["America/New_York", "Europe/London", "Australia/Sydney", "Australia/Lord_Howe"]
)
def test_offsets_around_every_transition_are_consistent(zone: str) -> None:
    for t in dst.transitions(zone, 2027):
        assert dst._offset(catalog.validate_zone(zone), int(t.instant_utc.timestamp()) - 1) == (
            t.offset_before
        )
    for s in dst.scenarios(zone):
        kind_after = s.case.id.split("-")
        t_utc = s.moment.astimezone(UTC)
        expected_after = any(k in kind_after for k in ("after", "second", "at"))
        offsets = {
            tr.offset_after if expected_after else tr.offset_before for tr in dst.transitions(zone)
        }
        assert s.moment.utcoffset() in offsets
        assert t_utc.year == 2027


def test_lord_howe_half_hour_shift() -> None:
    found = dst.transitions("Australia/Lord_Howe", 2027)
    assert len(found) == 2
    assert all(abs(t.offset_after - t.offset_before) == timedelta(minutes=30) for t in found)
    fall = next(t for t in found if not t.is_spring)
    scenarios = {s.case.id: s for s in dst.scenarios("Australia/Lord_Howe")}
    first = scenarios["dst-fall-first-repeat-2027"].moment
    second = scenarios["dst-fall-second-repeat-2027"].moment
    # Repeated period is 30 minutes long, so the passes sit 15 minutes either side.
    assert first.astimezone(UTC) == fall.instant_utc - timedelta(minutes=15)
    assert second.astimezone(UTC) == fall.instant_utc + timedelta(minutes=15)
    assert first.utcoffset() == fall.offset_before
    assert second.utcoffset() == fall.offset_after


def test_transition_note_text() -> None:
    notes = {s.case.id: s.note for s in dst.scenarios("America/New_York")}
    assert notes["dst-spring-before-2027"] == (
        "2027-03-14 02:00 local clocks jump to 03:00 (America/New_York)"
    )
    assert notes["dst-fall-after-2027"] == (
        "2027-11-07 02:00 local clocks go back to 01:00 (America/New_York)"
    )


def test_numbering_when_a_kind_repeats(monkeypatch: pytest.MonkeyPatch) -> None:
    ny_spring, ny_fall = dst.transitions("America/New_York", 2027)
    later_spring = ny_spring._replace(instant_utc=_utc(2027, 12, 1, 7, 0, 0))
    monkeypatch.setattr(
        dst, "transitions", lambda zone, year=2027: [ny_spring, ny_fall, later_spring]
    )
    ids = [s.case.id for s in dst.scenarios("America/New_York")]
    assert "dst-spring-1-before-2027" in ids
    assert "dst-spring-2-before-2027" in ids
    assert "dst-fall-before-2027" in ids  # only one fall: unnumbered


def test_expand_dst_multiple_zones_skips_zones_without_dst() -> None:
    found = catalog.expand(["dst"], ["UTC", "America/New_York", "Asia/Tokyo", "Europe/London"])
    zones = {s.zone for s in found}
    assert zones == {"America/New_York", "Europe/London"}
    assert len(found) == 16
    assert len({s.id for s in found}) == 16


def test_expand_dst_without_any_dst_zone_errors() -> None:
    with pytest.raises(ValueError, match=r'"dst" requested but none of zones \[.*UTC.*Tokyo.*\]'):
        catalog.expand(["dst"], ["UTC", "Asia/Tokyo"])


def test_expand_dst_mixes_with_other_presets_in_order() -> None:
    found = catalog.expand(["midnight", "dst"], ["America/New_York"])
    assert found[0].case.preset == "midnight"
    assert found[2].case.preset == "dst"


def test_transitions_are_cached_but_callers_get_a_fresh_list() -> None:
    first = dst.transitions("Europe/Paris", 2027)
    first.clear()  # mutating the returned list must not corrupt the cache
    assert len(dst.transitions("Europe/Paris", 2027)) == 2
    before = dst._transitions.cache_info().hits
    dst.transitions("Europe/Paris", 2027)
    assert dst._transitions.cache_info().hits == before + 1
