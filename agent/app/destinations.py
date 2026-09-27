"""Destinations the knowledge base covers (see CLAUDE.md "Known constraints")."""

from __future__ import annotations

KNOWN_DESTINATIONS = frozenset(
    {
        "da_nang_hoi_an",
        "bangkok",
        "almaty",
        "tokyo_fuji_hiroshima",
    }
)


DISPLAY_NAMES: dict[str, str] = {
    "da_nang_hoi_an": "Da Nang & Hoi An",
    "bangkok": "Bangkok",
    "almaty": "Almaty",
    "tokyo_fuji_hiroshima": "Tokyo, Fuji & Hiroshima",
}


def display_name(destination: str) -> str:
    """Human-readable name; free-text (non-guide) destinations are already one."""
    return DISPLAY_NAMES.get(destination, destination)


class UnknownDestinationError(Exception):
    """Raised when asked about a destination outside KNOWN_DESTINATIONS.

    Shared across tools (knowledge search, weather) - "not a destination
    we cover" is the same failure mode regardless of which tool hit it.
    """


class UnknownCityError(Exception):
    """Raised when `city` is given but isn't one of that destination's known cities."""


# (latitude, longitude) per destination - used for weather lookups.
# Multi-city destinations get a default (the first-listed city below);
# pass `city` to narrow to a specific one.
DESTINATION_COORDS: dict[str, tuple[float, float]] = {
    "da_nang_hoi_an": (16.0544, 108.2022),  # Da Nang
    "bangkok": (13.7563, 100.5018),
    "almaty": (43.2220, 76.8512),
    "tokyo_fuji_hiroshima": (35.6762, 139.6503),  # Tokyo
}

# Per-city coordinates within a destination that bundles several cities
# (mirrors the `city` filter on search_destination_knowledge).
CITY_COORDS: dict[str, dict[str, tuple[float, float]]] = {
    "da_nang_hoi_an": {
        "da_nang": (16.0544, 108.2022),
        "hoi_an": (15.8801, 108.3380),
    },
    "tokyo_fuji_hiroshima": {
        "tokyo": (35.6762, 139.6503),
        "fuji": (35.3606, 138.7274),
        "hiroshima": (34.3853, 132.4553),
    },
}


def destination_coords(destination: str, city: str | None = None) -> tuple[float, float]:
    """(lat, lon) for a known destination, optionally narrowed to one city.

    Caller is expected to have already checked `destination in
    KNOWN_DESTINATIONS`. A `city` is only meaningful for a destination
    that actually bundles several (CITY_COORDS has an entry for it) -
    for a single-city destination `city` is silently ignored rather
    than rejected, since an LLM redundantly echoing the destination
    name as `city` (e.g. city="bangkok") is a benign, observed case,
    not genuinely invalid input. Raises UnknownCityError only when the
    destination does have a per-city breakdown and `city` isn't one of
    its known cities.
    """
    city_map = CITY_COORDS.get(destination)
    if city_map is None:
        return DESTINATION_COORDS[destination]
    if city and city not in city_map:
        raise UnknownCityError(
            f"'{city}' is not a known city within '{destination}' "
            f"(known: {', '.join(sorted(city_map))})"
        )
    return city_map[city] if city else DESTINATION_COORDS[destination]
