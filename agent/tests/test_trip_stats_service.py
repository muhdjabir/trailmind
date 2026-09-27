import datetime
from unittest.mock import Mock, patch

from app.open_meteo import OpenMeteoError
from app.repositories.itinerary_repo import ItineraryDay
from app.repositories.trips_repo import Trip
from app.services.trip_stats_service import compute_trip_stats
from app.services.weather_service import WeatherResult


def _trip(**overrides) -> Trip:
    defaults = dict(
        id=1,
        user_id=None,
        name="Hoi An",
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


def _day(n: int) -> ItineraryDay:
    return ItineraryDay(id=n, trip_id=1, day_number=n, plan={"title": "x", "items": []},
                        updated_at=datetime.datetime(2026, 1, 1))


DATED = dict(
    destinations=["da_nang_hoi_an", "bangkok"],
    start_date=datetime.date(2026, 11, 6),
    end_date=datetime.date(2026, 11, 9),
)

WEATHER = WeatherResult("historical_average", datetime.date(2026, 11, 6),
                        datetime.date(2026, 11, 9), 27.0, 22.0, 60.0, 3)


@patch("app.services.trip_stats_service.get_weather", return_value=WEATHER)
@patch("app.services.trip_stats_service.list_days", return_value=[_day(1), _day(3)])
@patch("app.services.trip_stats_service.get_trip", return_value=_trip(**DATED, budget_planned=900))
def test_dated_trip_reports_open_days_and_weather_for_first_destination(
    mock_get_trip: Mock, mock_list_days: Mock, mock_weather: Mock
) -> None:
    stats = compute_trip_stats(Mock(), 1)

    assert stats.trip_days == 4
    assert stats.days_planned == 2
    assert stats.open_days == [2, 4]
    assert stats.budget_planned == 900
    assert stats.weather is WEATHER
    assert stats.weather_destination == "da_nang_hoi_an"
    assert stats.weather_error is None
    mock_weather.assert_called_once_with(
        "da_nang_hoi_an", datetime.date(2026, 11, 6), datetime.date(2026, 11, 9)
    )


@patch("app.services.trip_stats_service.get_weather")
@patch("app.services.trip_stats_service.list_days", return_value=[_day(1), _day(5)])
@patch("app.services.trip_stats_service.get_trip", return_value=_trip())
def test_open_dates_no_length_no_open_days_no_weather(
    mock_get_trip: Mock, mock_list_days: Mock, mock_weather: Mock
) -> None:
    stats = compute_trip_stats(Mock(), 1)

    assert stats.trip_days is None
    assert stats.days_planned == 2
    assert stats.open_days == []
    assert stats.weather is None
    assert stats.weather_error is None
    mock_weather.assert_not_called()


@patch("app.services.trip_stats_service.get_weather")
@patch("app.services.trip_stats_service.list_days", return_value=[])
@patch(
    "app.services.trip_stats_service.get_trip",
    return_value=_trip(start_date=datetime.date(2026, 11, 6), end_date=datetime.date(2026, 11, 7)),
)
def test_no_destination_skips_weather(
    mock_get_trip: Mock, mock_list_days: Mock, mock_weather: Mock
) -> None:
    stats = compute_trip_stats(Mock(), 1)

    assert stats.open_days == [1, 2]
    assert stats.weather is None
    mock_weather.assert_not_called()


@patch("app.services.trip_stats_service.get_weather", side_effect=OpenMeteoError("down"))
@patch("app.services.trip_stats_service.list_days", return_value=[])
@patch("app.services.trip_stats_service.get_trip", return_value=_trip(**DATED))
def test_weather_failure_reported_not_raised(
    mock_get_trip: Mock, mock_list_days: Mock, mock_weather: Mock
) -> None:
    stats = compute_trip_stats(Mock(), 1)

    assert stats.weather is None
    assert stats.weather_error == "down"
    assert stats.trip_days == 4
