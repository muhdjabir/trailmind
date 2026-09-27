"""Derived trip stats for the UI's stat cards (v1 step 22a).

Only what can actually be computed from stored state - no estimates.
Travel time / stay cost / walking distance (the mockup's cards) need
flights/hotels data (steps 18/19) and are added once that exists.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg

from app.destinations import UnknownCityError
from app.open_meteo import OpenMeteoError
from app.repositories.itinerary_repo import list_days
from app.repositories.trips_repo import get_trip
from app.services.itinerary_service import trip_length
from app.services.suggestions_service import build_suggestions
from app.services.weather_service import WeatherResult, get_weather


@dataclass
class TripStats:
    trip_days: int | None
    days_planned: int
    # Days within the trip's dates with nothing saved yet; empty while
    # the dates are open (no fixed length to be "open" against).
    open_days: list[int]
    budget_planned: float | None
    budget_total: float | None
    weather_destination: str | None
    weather: WeatherResult | None
    # Set when weather was attempted but failed - kept separate from
    # "not attempted" (no dates/destination) so the UI can tell them apart.
    weather_error: str | None
    # Follow-up chips (step 22b) - built here since the rain rule needs
    # the weather this already fetched; a separate endpoint would re-run
    # the slow Open-Meteo calls.
    suggestions: list[str]


def compute_trip_stats(conn: psycopg.Connection, trip_id: int) -> TripStats:
    """Raises TripNotFoundError for an unknown trip."""
    trip = get_trip(conn, trip_id)
    planned = {d.day_number for d in list_days(conn, trip_id)}
    length = trip_length(trip)
    open_days = [n for n in range(1, length + 1) if n not in planned] if length else []

    weather_destination = None
    weather = None
    weather_error = None
    if trip.start_date and trip.end_date and trip.destinations:
        # Multi-destination trips: first destination only, and labelled as
        # such in the response rather than blending locations.
        weather_destination = trip.destinations[0]
        try:
            weather = get_weather(weather_destination, trip.start_date, trip.end_date)
        except (OpenMeteoError, UnknownCityError, ValueError) as e:
            weather_error = str(e)

    return TripStats(
        trip_days=length,
        days_planned=len(planned),
        open_days=open_days,
        budget_planned=trip.budget_planned,
        budget_total=trip.budget_total,
        weather_destination=weather_destination,
        weather=weather,
        weather_error=weather_error,
        suggestions=build_suggestions(trip, length, len(planned), open_days, weather),
    )
