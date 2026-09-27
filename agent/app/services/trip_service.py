"""Trip-level details the agent can set: destinations, party size, budget."""

from __future__ import annotations

import psycopg

from app.destinations import KNOWN_DESTINATIONS
from app.repositories.trips_repo import Trip, update_trip_details


class InvalidTripDetailsError(Exception):
    """Raised when a trip detail update is empty or has a bad value."""


def _normalize_destination(name: str) -> str:
    # "Da Nang Hoi An" / "da-nang-hoi-an" → the known slug, so the curated
    # tools recognise it. Anything else is kept as the user's place name:
    # weather geocodes it, and search_web covers the rest.
    slug = name.strip().lower().replace("-", "_").replace(" ", "_")
    return slug if slug in KNOWN_DESTINATIONS else name.strip()


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def set_trip_details(
    conn: psycopg.Connection,
    trip_id: int,
    destinations: list[str] | None = None,
    party_size: int | None = None,
    budget_planned: float | None = None,
    budget_total: float | None = None,
) -> Trip:
    """Update whichever details are given; None means "leave as is".

    `destinations` replaces the whole list. Raises InvalidTripDetailsError
    for bad input, TripNotFoundError for an unknown trip.
    """
    fields: dict = {}

    if destinations is not None:
        if (
            not isinstance(destinations, list)
            or not destinations
            or not all(isinstance(d, str) and d.strip() for d in destinations)
        ):
            raise InvalidTripDetailsError("destinations must be a list of non-empty place names")
        fields["destinations"] = list(dict.fromkeys(_normalize_destination(d) for d in destinations))

    if party_size is not None:
        if not isinstance(party_size, int) or isinstance(party_size, bool) or party_size < 1:
            raise InvalidTripDetailsError(f"party_size must be a positive integer, got {party_size!r}")
        fields["party_size"] = party_size

    for name, value in (("budget_planned", budget_planned), ("budget_total", budget_total)):
        if value is not None:
            if not _is_number(value) or value < 0:
                raise InvalidTripDetailsError(f"{name} must be a non-negative number, got {value!r}")
            fields[name] = value

    if not fields:
        raise InvalidTripDetailsError("nothing to update - pass at least one detail")

    return update_trip_details(conn, trip_id, fields)
