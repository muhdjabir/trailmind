"""Itinerary business rules: what a valid day looks like and where it can go."""

from __future__ import annotations

import datetime

import psycopg

from app.repositories.itinerary_repo import (
    ItineraryDay,
    delete_day,
    delete_days_after,
    list_days,
    upsert_day,
)
from app.repositories.trips_repo import Trip, get_trip, update_trip_dates


class InvalidItineraryDayError(Exception):
    """Raised when a day's number or plan content can't be saved as given."""


class InvalidTripDatesError(Exception):
    """Raised when new trip dates are malformed or would strand saved days."""


def trip_length(trip: Trip) -> int | None:
    if trip.start_date and trip.end_date:
        return (trip.end_date - trip.start_date).days + 1
    return None


def day_date(trip: Trip, day_number: int) -> datetime.date | None:
    if trip.start_date is None:
        return None
    return trip.start_date + datetime.timedelta(days=day_number - 1)


def save_itinerary_day(
    conn: psycopg.Connection, trip_id: int, day: int, title: str, items: list[str]
) -> ItineraryDay:
    """Replace (or create) one day of a trip's itinerary.

    Whole-day replace, not a patch: the caller resends the full day.
    Raises InvalidItineraryDayError for bad input, TripNotFoundError for
    an unknown trip.
    """
    if not isinstance(day, int) or isinstance(day, bool) or day < 1:
        raise InvalidItineraryDayError(f"day must be a positive integer, got {day!r}")
    if not isinstance(title, str) or not title.strip():
        raise InvalidItineraryDayError("title must be a non-empty string")
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        raise InvalidItineraryDayError("items must be a list of strings")

    trip = get_trip(conn, trip_id)
    length = trip_length(trip)
    if length is not None and day > length:
        raise InvalidItineraryDayError(
            f"day {day} is outside this trip's dates ({trip.start_date} to "
            f"{trip.end_date}, {length} days)"
        )

    plan = {"title": title.strip(), "items": [i.strip() for i in items if i.strip()]}
    return upsert_day(conn, trip_id, day, plan)


def delete_itinerary_day(conn: psycopg.Connection, trip_id: int, day: int) -> None:
    """Clear one day. Other days keep their numbers - no renumbering."""
    if not isinstance(day, int) or isinstance(day, bool) or day < 1:
        raise InvalidItineraryDayError(f"day must be a positive integer, got {day!r}")
    if not delete_day(conn, trip_id, day):
        raise InvalidItineraryDayError(f"day {day} has nothing saved, so there's nothing to delete")


def change_trip_dates(
    conn: psycopg.Connection,
    trip_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    drop_days_past_end: bool = False,
) -> tuple[Trip, list[int]]:
    """Set, move, extend or shorten a trip's dates.

    Day dates are derived from start_date, so moving the trip needs no
    itinerary rewrite. By default, shortening is refused while saved days
    would fall past the new end. `drop_days_past_end=True` deletes those
    days instead, in the same call - one step rather than delete-then-
    shorten, which the local model often left half done. Returns the trip
    and the day numbers that were dropped.
    """
    if end_date < start_date:
        raise InvalidTripDatesError(f"end date {end_date} is before start date {start_date}")

    new_length = (end_date - start_date).days + 1
    stranded = [d.day_number for d in list_days(conn, trip_id) if d.day_number > new_length]
    dropped: list[int] = []
    if stranded:
        if not drop_days_past_end:
            days = ", ".join(str(n) for n in stranded)
            raise InvalidTripDatesError(
                f"the new dates make the trip {new_length} days, but day(s) {days} "
                "still have saved plans. If the user wants those days dropped, "
                "call again with drop_days_past_end=true; otherwise ask them "
                "first, or resave those plans into earlier days"
            )
        dropped = delete_days_after(conn, trip_id, new_length)
    return update_trip_dates(conn, trip_id, start_date, end_date), dropped
