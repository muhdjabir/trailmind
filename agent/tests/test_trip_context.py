import datetime

from app.repositories.itinerary_repo import ItineraryDay
from app.repositories.trips_repo import Trip
from app.services.trip_context import trip_summary


def _trip(**overrides) -> Trip:
    defaults = dict(
        id=1,
        user_id=None,
        name="Da Nang & Hoi An 2026",
        destinations=[],
        start_date=None,
        end_date=None,
        party_size=None,
        status="draft",
        budget_planned=None,
        budget_total=None,
        created_at=datetime.datetime(2026, 1, 1),
        updated_at=datetime.datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return Trip(**defaults)


def test_summary_includes_name_and_status() -> None:
    summary = trip_summary(_trip())
    assert "Da Nang & Hoi An 2026" in summary
    assert "draft" in summary


def test_summary_includes_destinations_when_present() -> None:
    summary = trip_summary(_trip(destinations=["da_nang_hoi_an", "bangkok"]))
    assert "da_nang_hoi_an" in summary
    assert "bangkok" in summary


def test_summary_omits_empty_fields() -> None:
    summary = trip_summary(_trip())
    assert "Destinations" not in summary
    assert "Party size" not in summary
    assert "Budget" not in summary


def test_summary_includes_dates_party_and_budget_when_present() -> None:
    summary = trip_summary(
        _trip(
            start_date=datetime.date(2026, 11, 1),
            end_date=datetime.date(2026, 11, 8),
            party_size=2,
            budget_planned=1200,
            budget_total=2000,
        )
    )
    assert "2026-11-01" in summary
    assert "2026-11-08" in summary
    assert "Party size: 2" in summary
    assert "1200" in summary
    assert "2000" in summary


def _day(day_number: int, title: str, items: list[str]) -> ItineraryDay:
    return ItineraryDay(
        id=day_number,
        trip_id=1,
        day_number=day_number,
        plan={"title": title, "items": items},
        updated_at=datetime.datetime(2026, 1, 1),
    )


def test_summary_includes_itinerary_titles_and_items() -> None:
    summary = trip_summary(
        _trip(),
        [_day(1, "Arrive Lisbon", ["Check in Alfama", "Miradouro"]), _day(2, "Slow day", [])],
    )
    assert "Day 1: Arrive Lisbon (Check in Alfama · Miradouro)" in summary
    assert "Day 2: Slow day" in summary


def test_summary_omits_itinerary_when_no_days() -> None:
    assert "Itinerary" not in trip_summary(_trip(), [])
