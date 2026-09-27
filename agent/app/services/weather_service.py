"""get_weather tool (CLAUDE.md v1 step 17).

Real forecast for dates within Open-Meteo's ~16-day horizon; for
farther-out trip dates (the common case - people plan trips months
ahead), falls back to a "typical weather" average over the same
calendar dates in the last few years. Returns raw structured numbers,
not a pre-written summary - the agent's own reply synthesizes it,
same as search_destination_knowledge returning snippets rather than
conclusions.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from app.destinations import KNOWN_DESTINATIONS, destination_coords
from app.open_meteo import OpenMeteoError, fetch_archive, fetch_forecast, geocode

FORECAST_HORIZON_DAYS = 16
HISTORICAL_YEARS_BACK = 3


@dataclass
class WeatherResult:
    source: str  # "forecast" or "historical_average"
    start_date: datetime.date
    end_date: datetime.date
    avg_high_c: float
    avg_low_c: float
    total_precipitation_mm: float
    # "forecast": number of days the average is over. "historical_average":
    # number of past years successfully sampled (see get_weather).
    days_sampled: int


def _daily_stats(daily: dict) -> tuple[float, float, float, int]:
    n = len(daily["time"])
    if n == 0:
        raise OpenMeteoError("Open-Meteo returned zero days of data")
    avg_high = sum(daily["temperature_2m_max"]) / n
    avg_low = sum(daily["temperature_2m_min"]) / n
    total_precip = sum(daily["precipitation_sum"])
    return avg_high, avg_low, total_precip, n


def get_weather(
    destination: str,
    start_date: datetime.date,
    end_date: datetime.date,
    city: str | None = None,
) -> WeatherResult:
    """Weather for `destination` (optionally narrowed to `city`) over a date range.

    `destination` doesn't have to be in KNOWN_DESTINATIONS - weather
    isn't gated on curated-knowledge-base coverage the way
    search_destination_knowledge is. A known destination uses its
    hardcoded coordinates (app.destinations); anything else is
    geocoded from the free-text name instead.

    Raises UnknownCityError, ValueError (bad date range), or
    OpenMeteoError (including "place not found" from geocoding) -
    never returns a silently-empty result; the caller decides how to
    handle each.
    """
    if end_date < start_date:
        raise ValueError(f"end_date ({end_date}) is before start_date ({start_date})")

    if destination in KNOWN_DESTINATIONS:
        lat, lon = destination_coords(destination, city)
    else:
        place = f"{city}, {destination}" if city else destination
        lat, lon = geocode(place)

    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=FORECAST_HORIZON_DAYS)

    if start_date <= horizon:
        clipped_end = min(end_date, horizon)
        daily = fetch_forecast(lat, lon, start_date, clipped_end)
        avg_high, avg_low, total_precip, n = _daily_stats(daily)
        return WeatherResult("forecast", start_date, clipped_end, avg_high, avg_low, total_precip, n)

    # Too far out for a real forecast - average the same calendar range
    # across the past few years as a "typical weather" estimate. A
    # single year's data being unavailable (transient error, or the
    # range hits Feb 29 in a non-leap year) shouldn't sink the whole
    # average; days_sampled reports how many years actually landed.
    highs, lows, precips = [], [], []
    for years_back in range(1, HISTORICAL_YEARS_BACK + 1):
        try:
            hist_start = start_date.replace(year=start_date.year - years_back)
            hist_end = end_date.replace(year=end_date.year - years_back)
        except ValueError:
            continue
        try:
            daily = fetch_archive(lat, lon, hist_start, hist_end)
        except OpenMeteoError:
            continue
        avg_high, avg_low, total_precip, _ = _daily_stats(daily)
        highs.append(avg_high)
        lows.append(avg_low)
        precips.append(total_precip)

    if not highs:
        raise OpenMeteoError(
            f"couldn't fetch any historical weather data for {destination} "
            f"({HISTORICAL_YEARS_BACK} years attempted)"
        )

    years_used = len(highs)
    return WeatherResult(
        "historical_average",
        start_date,
        end_date,
        sum(highs) / years_used,
        sum(lows) / years_used,
        sum(precips) / years_used,
        years_used,
    )
