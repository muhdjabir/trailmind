"""Follow-up suggestion chips from trip state (v1 step 22b).

Rule-based, not LLM-generated (user-confirmed): each chip is something
the trip is actually missing or likely to need, phrased as a message the
user would send - so every chip is something the agent can act on.
"""

from __future__ import annotations

from app.destinations import display_name
from app.repositories.trips_repo import Trip
from app.services.weather_service import WeatherResult

MAX_SUGGESTIONS = 3
# Average rain per day (mm) at or above which a rain backup plan is worth
# suggesting - roughly "moderate rain" territory.
RAINY_MM_PER_DAY = 5.0


def build_suggestions(
    trip: Trip,
    trip_days: int | None,
    days_planned: int,
    open_days: list[int],
    weather: WeatherResult | None,
) -> list[str]:
    """Up to MAX_SUGGESTIONS chips, most useful first."""
    name = display_name(trip.destinations[0]) if trip.destinations else None
    chips: list[str] = []

    if name is None:
        chips.append("Help us pick a destination")
    elif trip_days is None:
        chips.append(f"When's the best time to visit {name}?")

    if trip_days is not None:
        if days_planned == 0:
            chips.append("Plan the whole trip day by day")
        elif open_days:
            chips.append(f"Plan day {open_days[0]}")

    if weather is not None:
        # end_date may be clipped to the forecast horizon, so average over
        # the range the weather actually covers, not the whole trip.
        days = (weather.end_date - weather.start_date).days + 1
        if weather.total_precipitation_mm / days >= RAINY_MM_PER_DAY:
            chips.append("What can we do if it rains?")

    if name is not None:
        chips.append(f"Where to eat in {name}?")
        if trip.budget_total is None:
            chips.append("How much should we budget?")

    if trip_days is not None and days_planned > 0 and not open_days:
        chips.append("What are we missing?")

    return chips[:MAX_SUGGESTIONS]
