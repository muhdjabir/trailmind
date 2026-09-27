"""ICS calendar export of a trip's itinerary (v1 step 22c).

Hand-rolled rather than a dependency: all-day events only, and RFC 5545's
rules that matter here (CRLF line endings, text escaping, 75-octet line
folding) are a few lines each.
"""

from __future__ import annotations

import datetime

from app.destinations import display_name
from app.repositories.itinerary_repo import ItineraryDay
from app.repositories.trips_repo import Trip
from app.services.itinerary_service import day_date


class TripNotDatedError(Exception):
    """Raised when exporting a trip that has no start date - days have no dates yet."""


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Split into lines of at most 75 octets, never inside a UTF-8 character."""
    chunks: list[str] = []
    current, size = "", 0
    for ch in line:
        width = len(ch.encode("utf-8"))
        # Continuation lines start with a space, which counts toward 75.
        limit = 75 if not chunks else 74
        if size + width > limit:
            chunks.append(current)
            current, size = "", 0
        current += ch
        size += width
    chunks.append(current)
    return "\r\n ".join(chunks)


def _stamp(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_trip_ics(trip: Trip, days: list[ItineraryDay]) -> str:
    """One all-day event per saved day. Raises TripNotDatedError if undated."""
    if trip.start_date is None:
        raise TripNotDatedError("this trip has no dates yet, so its days can't go on a calendar")

    location = ", ".join(display_name(d) for d in trip.destinations)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//trailmind//itinerary export//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(trip.name)}",
    ]
    for day in days:
        date = day_date(trip, day.day_number)
        title = day.plan.get("title", "")
        items = day.plan.get("items", [])
        lines += [
            "BEGIN:VEVENT",
            # Stable per trip+day, so re-importing updates events instead
            # of duplicating them.
            f"UID:trip-{trip.id}-day-{day.day_number}@trailmind",
            f"DTSTAMP:{_stamp(day.updated_at)}",
            f"DTSTART;VALUE=DATE:{date:%Y%m%d}",
            f"DTEND;VALUE=DATE:{date + datetime.timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_escape(f'Day {day.day_number}: {title}')}",
        ]
        if items:
            lines.append(f"DESCRIPTION:{_escape(chr(10).join(items))}")
        if location:
            lines.append(f"LOCATION:{_escape(location)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "".join(_fold(line) + "\r\n" for line in lines)
