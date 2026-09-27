import datetime

import pytest

from app.repositories.itinerary_repo import ItineraryDay
from app.repositories.trips_repo import Trip
from app.services.calendar_service import TripNotDatedError, _fold, build_trip_ics


def _trip(**overrides) -> Trip:
    defaults = dict(
        id=7, user_id=None, name="Hoi An, long weekend", destinations=["da_nang_hoi_an"],
        start_date=datetime.date(2026, 11, 6), end_date=datetime.date(2026, 11, 9),
        party_size=2, status="draft", budget_planned=None, budget_total=None,
        created_at=datetime.datetime(2026, 1, 1), updated_at=datetime.datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return Trip(**defaults)


def _day(n: int, title: str, items: list[str]) -> ItineraryDay:
    return ItineraryDay(
        id=n, trip_id=7, day_number=n, plan={"title": title, "items": items},
        updated_at=datetime.datetime(2026, 9, 27, 3, 0, tzinfo=datetime.timezone.utc),
    )


def _unfold(ics: str) -> list[str]:
    return ics.replace("\r\n ", "").split("\r\n")


def test_one_all_day_event_per_saved_day() -> None:
    ics = build_trip_ics(_trip(), [_day(1, "Arrive", ["Old Town walk"]), _day(3, "Beach", [])])
    lines = _unfold(ics)

    assert lines[0] == "BEGIN:VCALENDAR" and lines[-2] == "END:VCALENDAR" and lines[-1] == ""
    assert lines.count("BEGIN:VEVENT") == 2
    assert "UID:trip-7-day-1@trailmind" in lines
    assert "DTSTART;VALUE=DATE:20261106" in lines
    assert "DTEND;VALUE=DATE:20261107" in lines
    # Day 3 lands on the trip's third date, not the next event slot.
    assert "DTSTART;VALUE=DATE:20261108" in lines
    assert "SUMMARY:Day 1: Arrive" in lines
    assert "DESCRIPTION:Old Town walk" in lines
    assert "LOCATION:Da Nang & Hoi An" in lines
    assert "DTSTAMP:20260927T030000Z" in lines
    assert "X-WR-CALNAME:Hoi An\\, long weekend" in lines


def test_every_line_ends_with_crlf() -> None:
    ics = build_trip_ics(_trip(), [_day(1, "Arrive", ["a", "b"])])
    assert ics.endswith("\r\n")
    assert "\n" not in ics.replace("\r\n", "")


def test_text_is_escaped() -> None:
    ics = build_trip_ics(_trip(), [_day(1, "Food; drinks, etc", ["Pho\\noodles", "Bar"])])
    lines = _unfold(ics)
    assert "SUMMARY:Day 1: Food\\; drinks\\, etc" in lines
    assert "DESCRIPTION:Pho\\\\noodles\\nBar" in lines


def test_long_lines_folded_to_75_octets_without_splitting_utf8() -> None:
    line = "DESCRIPTION:" + "Phở bò · " * 20
    folded = _fold(line)
    for part in folded.split("\r\n"):
        assert len(part.encode("utf-8")) <= 75
    assert folded.replace("\r\n ", "") == line


def test_undated_trip_raises() -> None:
    with pytest.raises(TripNotDatedError):
        build_trip_ics(_trip(start_date=None, end_date=None), [_day(1, "x", [])])


def test_no_location_line_without_destinations() -> None:
    ics = build_trip_ics(_trip(destinations=[]), [_day(1, "x", [])])
    assert "LOCATION" not in ics
