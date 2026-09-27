import datetime
from unittest.mock import Mock, patch

import pytest

from app.open_meteo import OpenMeteoError
from app.services.weather_service import get_weather

FORECAST_DAILY = {
    "time": ["d1", "d2"],
    "temperature_2m_max": [30.0, 32.0],
    "temperature_2m_min": [24.0, 26.0],
    "precipitation_sum": [2.0, 0.0],
}


@patch("app.services.weather_service.geocode")
@patch("app.services.weather_service.fetch_forecast")
def test_destination_outside_known_list_is_geocoded(
    mock_fetch_forecast: Mock, mock_geocode: Mock
) -> None:
    # Weather isn't gated on curated-knowledge coverage the way
    # search_destination_knowledge is - a destination outside
    # KNOWN_DESTINATIONS falls back to geocoding the free-text name
    # rather than raising.
    mock_geocode.return_value = (48.8534, 2.3488)
    mock_fetch_forecast.return_value = FORECAST_DAILY
    today = datetime.date.today()

    result = get_weather("paris", today + datetime.timedelta(days=1), today + datetime.timedelta(days=2))

    mock_geocode.assert_called_once_with("paris")
    mock_fetch_forecast.assert_called_once_with(48.8534, 2.3488, today + datetime.timedelta(days=1),
                                                 today + datetime.timedelta(days=2))
    assert result.source == "forecast"


@patch("app.services.weather_service.geocode", side_effect=OpenMeteoError("no location found for 'nowhereville'"))
def test_geocoding_failure_raises_open_meteo_error(mock_geocode: Mock) -> None:
    today = datetime.date.today()
    with pytest.raises(OpenMeteoError, match="nowhereville"):
        get_weather("nowhereville", today + datetime.timedelta(days=1), today + datetime.timedelta(days=2))


def test_end_before_start_raises_value_error() -> None:
    with pytest.raises(ValueError):
        get_weather("bangkok", datetime.date(2026, 11, 5), datetime.date(2026, 11, 1))


@patch("app.services.weather_service.fetch_forecast")
def test_near_term_dates_use_forecast(mock_fetch_forecast: Mock) -> None:
    mock_fetch_forecast.return_value = FORECAST_DAILY
    today = datetime.date.today()
    start = today + datetime.timedelta(days=2)
    end = today + datetime.timedelta(days=3)

    result = get_weather("bangkok", start, end)

    assert result.source == "forecast"
    assert result.avg_high_c == pytest.approx(31.0)
    assert result.avg_low_c == pytest.approx(25.0)
    assert result.total_precipitation_mm == pytest.approx(2.0)
    assert result.days_sampled == 2
    mock_fetch_forecast.assert_called_once()


@patch("app.services.weather_service.fetch_archive")
def test_far_future_dates_use_historical_average(mock_fetch_archive: Mock) -> None:
    mock_fetch_archive.return_value = FORECAST_DAILY
    far_start = datetime.date.today() + datetime.timedelta(days=200)
    far_end = far_start + datetime.timedelta(days=1)

    result = get_weather("bangkok", far_start, far_end)

    assert result.source == "historical_average"
    assert result.days_sampled == 3  # HISTORICAL_YEARS_BACK
    assert mock_fetch_archive.call_count == 3


@patch("app.services.weather_service.fetch_archive")
def test_one_failed_historical_year_does_not_sink_the_average(mock_fetch_archive: Mock) -> None:
    mock_fetch_archive.side_effect = [
        OpenMeteoError("transient"),
        FORECAST_DAILY,
        FORECAST_DAILY,
    ]
    far_start = datetime.date.today() + datetime.timedelta(days=200)
    far_end = far_start + datetime.timedelta(days=1)

    result = get_weather("bangkok", far_start, far_end)

    assert result.source == "historical_average"
    assert result.days_sampled == 2


@patch("app.services.weather_service.fetch_archive")
def test_all_historical_years_failing_raises_open_meteo_error(mock_fetch_archive: Mock) -> None:
    mock_fetch_archive.side_effect = OpenMeteoError("down")
    far_start = datetime.date.today() + datetime.timedelta(days=200)
    far_end = far_start + datetime.timedelta(days=1)

    with pytest.raises(OpenMeteoError):
        get_weather("bangkok", far_start, far_end)


@patch("app.services.weather_service.fetch_forecast")
def test_city_argument_resolves_to_city_specific_coords(mock_fetch_forecast: Mock) -> None:
    mock_fetch_forecast.return_value = FORECAST_DAILY
    today = datetime.date.today()

    get_weather(
        "da_nang_hoi_an", today + datetime.timedelta(days=1), today + datetime.timedelta(days=2),
        city="hoi_an",
    )

    lat, lon = mock_fetch_forecast.call_args[0][:2]
    from app.destinations import destination_coords

    assert (lat, lon) == destination_coords("da_nang_hoi_an", city="hoi_an")
