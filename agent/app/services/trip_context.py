"""Formatting trip state for the agent's LLM context (CLAUDE.md "State model").

Separate from app.repositories.trips_repo on purpose: this is about how
to represent a Trip to the LLM, not about persisting one.
"""

from __future__ import annotations

from app.repositories.itinerary_repo import ItineraryDay
from app.repositories.trips_repo import Trip


def trip_summary(trip: Trip, days: list[ItineraryDay] | None = None) -> str:
    """Compact one-line-ish description of trip state for the agent's context.

    Deliberately a short derived summary, not a dump of the full row/
    itinerary - see CLAUDE.md "State model" (re-hydrate a compact summary
    each turn, not the full conversation/state).
    """
    parts = [f"Trip \"{trip.name}\" (status: {trip.status})"]
    if trip.destinations:
        parts.append(f"Destinations: {', '.join(trip.destinations)}")
    if trip.start_date and trip.end_date:
        length = (trip.end_date - trip.start_date).days + 1
        parts.append(f"Dates: {trip.start_date} to {trip.end_date} ({length} days)")
    if trip.party_size:
        parts.append(f"Party size: {trip.party_size}")
    if trip.budget_planned or trip.budget_total:
        parts.append(f"Budget: {trip.budget_planned or '?'} planned / {trip.budget_total or '?'} total")
    if days:
        # Items included, not just titles: save_itinerary_day replaces a
        # whole day, so editing one needs its existing items to resend.
        outline = "; ".join(
            f"Day {d.day_number}: {d.plan.get('title', '')}"
            + (f" ({' · '.join(d.plan['items'])})" if d.plan.get("items") else "")
            for d in days
        )
        parts.append(f"Itinerary so far: {outline}")
    return ". ".join(parts) + "."
