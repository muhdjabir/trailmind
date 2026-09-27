import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from app.open_meteo import OpenMeteoError, fetch_archive, fetch_forecast

SAMPLE_DAILY = {
    "time": ["2026-11-01", "2026-11-02"],
    "temperature_2m_max": [30.0, 31.0],
    "temperature_2m_min": [24.0, 25.0],
    "precipitation_sum": [1.0, 0.0],
}


@patch("app.open_meteo.requests.get")
def test_fetch_forecast_returns_daily_dict(mock_get: Mock) -> None:
    mock_get.return_value = Mock(status_code=200, json=lambda: {"daily": SAMPLE_DAILY})
    result = fetch_forecast(13.7, 100.5, datetime.date(2026, 11, 1), datetime.date(2026, 11, 2))
    assert result == SAMPLE_DAILY


@patch("app.open_meteo.requests.get")
def test_fetch_archive_returns_daily_dict(mock_get: Mock) -> None:
    mock_get.return_value = Mock(status_code=200, json=lambda: {"daily": SAMPLE_DAILY})
    result = fetch_archive(13.7, 100.5, datetime.date(2025, 11, 1), datetime.date(2025, 11, 2))
    assert result == SAMPLE_DAILY


@patch("app.open_meteo.requests.get")
def test_connection_error_raises_open_meteo_error(mock_get: Mock) -> None:
    mock_get.side_effect = requests.ConnectionError("refused")
    with pytest.raises(OpenMeteoError, match="could not reach"):
        fetch_forecast(13.7, 100.5, datetime.date(2026, 11, 1), datetime.date(2026, 11, 2))


@patch("app.open_meteo.requests.get")
def test_non_200_raises_open_meteo_error(mock_get: Mock) -> None:
    mock_get.return_value = Mock(status_code=400, text="bad request")
    with pytest.raises(OpenMeteoError, match="400"):
        fetch_forecast(13.7, 100.5, datetime.date(2026, 11, 1), datetime.date(2026, 11, 2))


@patch("app.open_meteo.requests.get")
def test_missing_daily_key_raises_open_meteo_error(mock_get: Mock) -> None:
    mock_get.return_value = Mock(status_code=200, json=lambda: {"unexpected": "shape"})
    with pytest.raises(OpenMeteoError, match="unexpected"):
        fetch_forecast(13.7, 100.5, datetime.date(2026, 11, 1), datetime.date(2026, 11, 2))
