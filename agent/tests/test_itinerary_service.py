import datetime
from unittest.mock import Mock, patch

import pytest

from app.repositories.trips_repo import Trip
from app.repositories.itinerary_repo import ItineraryDay
from app.services.itinerary_service import (
    InvalidItineraryDayError,
    InvalidTripDatesError,
    change_trip_dates,
    day_date,
    delete_itinerary_day,
    save_itinerary_day,
)


def _trip(**overrides) -> Trip:
    defaults = dict(
        id=1,
        user_id=None,
        name="Lisbon & Porto",
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


DATED_TRIP = _trip(start_date=datetime.date(2026, 10, 12), end_date=datetime.date(2026, 10, 17))


@patch("app.services.itinerary_service.upsert_day")
@patch("app.services.itinerary_service.get_trip", return_value=DATED_TRIP)
def test_saves_trimmed_plan(mock_get_trip: Mock, mock_upsert: Mock) -> None:
    conn = Mock()
    save_itinerary_day(conn, 1, 3, "  Sintra day trip ", ["Train 09:10", " Pena ", ""])

    mock_upsert.assert_called_once_with(
        conn, 1, 3, {"title": "Sintra day trip", "items": ["Train 09:10", "Pena"]}
    )


@patch("app.services.itinerary_service.upsert_day")
@patch("app.services.itinerary_service.get_trip", return_value=DATED_TRIP)
def test_day_past_trip_end_rejected(mock_get_trip: Mock, mock_upsert: Mock) -> None:
    with pytest.raises(InvalidItineraryDayError, match="outside this trip's dates"):
        save_itinerary_day(Mock(), 1, 7, "Extra day", [])
    mock_upsert.assert_not_called()


@patch("app.services.itinerary_service.upsert_day")
@patch("app.services.itinerary_service.get_trip", return_value=_trip())
def test_any_positive_day_allowed_when_dates_open(mock_get_trip: Mock, mock_upsert: Mock) -> None:
    save_itinerary_day(Mock(), 1, 12, "Somewhere", [])
    mock_upsert.assert_called_once()


@pytest.mark.parametrize(
    "day,title,items",
    [
        (0, "t", []),
        (-1, "t", []),
        ("2", "t", []),
        (True, "t", []),
        (1, "   ", []),
        (1, "t", "Pena, Regaleira"),
        (1, "t", ["ok", 3]),
    ],
)
@patch("app.services.itinerary_service.upsert_day")
@patch("app.services.itinerary_service.get_trip", return_value=_trip())
def test_invalid_input_rejected_before_touching_db(
    mock_get_trip: Mock, mock_upsert: Mock, day, title, items
) -> None:
    with pytest.raises(InvalidItineraryDayError):
        save_itinerary_day(Mock(), 1, day, title, items)
    mock_get_trip.assert_not_called()
    mock_upsert.assert_not_called()


def test_day_date_derived_from_start_date() -> None:
    assert day_date(DATED_TRIP, 1) == datetime.date(2026, 10, 12)
    assert day_date(DATED_TRIP, 4) == datetime.date(2026, 10, 15)


def test_day_date_none_when_dates_open() -> None:
    assert day_date(_trip(), 1) is None


def _saved(day_number: int) -> ItineraryDay:
    return ItineraryDay(id=day_number, trip_id=1, day_number=day_number,
                        plan={"title": "x", "items": []},
                        updated_at=datetime.datetime(2026, 1, 1))


@patch("app.services.itinerary_service.delete_day", return_value=True)
def test_delete_itinerary_day_deletes(mock_delete: Mock) -> None:
    conn = Mock()
    delete_itinerary_day(conn, 1, 2)
    mock_delete.assert_called_once_with(conn, 1, 2)


@patch("app.services.itinerary_service.delete_day", return_value=False)
def test_delete_itinerary_day_with_nothing_saved_raises(mock_delete: Mock) -> None:
    with pytest.raises(InvalidItineraryDayError, match="nothing saved"):
        delete_itinerary_day(Mock(), 1, 2)


@patch("app.services.itinerary_service.delete_day")
def test_delete_itinerary_day_rejects_bad_day(mock_delete: Mock) -> None:
    with pytest.raises(InvalidItineraryDayError):
        delete_itinerary_day(Mock(), 1, 0)
    mock_delete.assert_not_called()


@patch("app.services.itinerary_service.update_trip_dates")
@patch("app.services.itinerary_service.list_days", return_value=[_saved(1), _saved(4)])
def test_extending_trip_updates_dates(mock_list_days: Mock, mock_update: Mock) -> None:
    conn = Mock()
    change_trip_dates(conn, 1, datetime.date(2026, 11, 6), datetime.date(2026, 11, 11))
    mock_update.assert_called_once_with(conn, 1, datetime.date(2026, 11, 6), datetime.date(2026, 11, 11))


@patch("app.services.itinerary_service.update_trip_dates")
@patch("app.services.itinerary_service.list_days", return_value=[_saved(1), _saved(4), _saved(5)])
def test_shortening_past_saved_days_refused(mock_list_days: Mock, mock_update: Mock) -> None:
    with pytest.raises(InvalidTripDatesError, match=r"day\(s\) 4, 5"):
        change_trip_dates(Mock(), 1, datetime.date(2026, 11, 6), datetime.date(2026, 11, 8))
    mock_update.assert_not_called()


@patch("app.services.itinerary_service.update_trip_dates")
@patch("app.services.itinerary_service.delete_days_after", return_value=[4, 5])
@patch("app.services.itinerary_service.list_days", return_value=[_saved(1), _saved(4), _saved(5)])
def test_shortening_with_drop_deletes_past_days_then_updates(
    mock_list_days: Mock, mock_delete_after: Mock, mock_update: Mock
) -> None:
    conn = Mock()
    trip, dropped = change_trip_dates(
        conn, 1, datetime.date(2026, 11, 6), datetime.date(2026, 11, 8), drop_days_past_end=True
    )

    mock_delete_after.assert_called_once_with(conn, 1, 3)
    mock_update.assert_called_once_with(conn, 1, datetime.date(2026, 11, 6), datetime.date(2026, 11, 8))
    assert dropped == [4, 5]
    assert trip is mock_update.return_value


@patch("app.services.itinerary_service.update_trip_dates")
@patch("app.services.itinerary_service.delete_days_after")
@patch("app.services.itinerary_service.list_days", return_value=[_saved(1)])
def test_drop_flag_deletes_nothing_when_no_days_stranded(
    mock_list_days: Mock, mock_delete_after: Mock, mock_update: Mock
) -> None:
    _, dropped = change_trip_dates(
        Mock(), 1, datetime.date(2026, 11, 6), datetime.date(2026, 11, 8), drop_days_past_end=True
    )
    mock_delete_after.assert_not_called()
    assert dropped == []


@patch("app.services.itinerary_service.update_trip_dates")
@patch("app.services.itinerary_service.list_days", return_value=[_saved(1), _saved(2)])
def test_shortening_with_no_days_past_new_end_allowed(mock_list_days: Mock, mock_update: Mock) -> None:
    change_trip_dates(Mock(), 1, datetime.date(2026, 11, 6), datetime.date(2026, 11, 7))
    mock_update.assert_called_once()


@patch("app.services.itinerary_service.update_trip_dates")
@patch("app.services.itinerary_service.list_days", return_value=[])
def test_end_before_start_refused(mock_list_days: Mock, mock_update: Mock) -> None:
    with pytest.raises(InvalidTripDatesError, match="before start"):
        change_trip_dates(Mock(), 1, datetime.date(2026, 11, 8), datetime.date(2026, 11, 6))
    mock_update.assert_not_called()
