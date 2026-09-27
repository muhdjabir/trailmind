"""Daily weather data via Open-Meteo (free, no API key/cost - see CLAUDE.md
"LLM & embeddings backend" for the project's general preference for this).

Two endpoints:
- /v1/forecast: real forecast, ~16 days ahead from today.
- /v1/archive: historical daily weather for a past date range, used by
  app.services.weather_service to build a "typical weather" average for
  trip dates too far out for a real forecast.
"""

from __future__ import annotations

import datetime

import requests

FORECAST_BASE_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,precipitation_sum"


class OpenMeteoError(Exception):
    """Typed error for Open-Meteo failures (unreachable, bad response, etc.)."""


def _fetch_daily(
    base_url: str,
    lat: float,
    lon: float,
    start_date: datetime.date,
    end_date: datetime.date,
    timeout: float,
) -> dict:
    try:
        response = requests.get(
            base_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": DAILY_FIELDS,
                "timezone": "auto",
            },
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise OpenMeteoError(f"could not reach Open-Meteo at {base_url}: {e}") from e

    if response.status_code != 200:
        raise OpenMeteoError(f"Open-Meteo returned {response.status_code}: {response.text}")

    data = response.json()
    daily = data.get("daily")
    if not daily or "time" not in daily:
        raise OpenMeteoError(f"unexpected Open-Meteo response shape: {data}")
    return daily


def fetch_forecast(
    lat: float,
    lon: float,
    start_date: datetime.date,
    end_date: datetime.date,
    timeout: float = 10.0,
) -> dict:
    """Daily forecast fields for [start_date, end_date] (must be within ~16 days out)."""
    return _fetch_daily(FORECAST_BASE_URL, lat, lon, start_date, end_date, timeout)


def fetch_archive(
    lat: float,
    lon: float,
    start_date: datetime.date,
    end_date: datetime.date,
    timeout: float = 10.0,
) -> dict:
    """Daily historical fields for [start_date, end_date] (must be in the past)."""
    return _fetch_daily(ARCHIVE_BASE_URL, lat, lon, start_date, end_date, timeout)
