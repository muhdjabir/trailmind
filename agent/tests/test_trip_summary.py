import datetime

from app.repositories.trips_repo import Trip, trip_summary


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
