"""Chat service: the single-agent reasoning loop over search_destination_knowledge.

CLAUDE.md v2 note: no subagent split yet - this is the one agent.
Tool failures aren't caught-and-hidden; they're fed back into the
conversation as the tool result, so the LLM's own next turn decides
how to explain it to the user (matches CLAUDE.md's "agent decides
retry/surface, no fixed policy").
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import re

import psycopg

from app.destinations import KNOWN_DESTINATIONS, UnknownCityError, UnknownDestinationError
from app.embeddings import EmbeddingError
from app.llm import LLMClient, OllamaLLMClient
from app.open_meteo import OpenMeteoError
from app.repositories.chat_history_repo import append_message, list_messages
from app.repositories.itinerary_repo import list_days
from app.repositories.trips_repo import get_trip
from app.repositories.vector_store_repo import VectorStoreError
from app.services.itinerary_service import (
    InvalidItineraryDayError,
    InvalidTripDatesError,
    change_trip_dates,
    delete_itinerary_day,
    save_itinerary_day,
    trip_length,
)
from app.services.knowledge_service import search_destination_knowledge
from app.services.trip_context import trip_summary
from app.services.trip_service import InvalidTripDetailsError, set_trip_details
from app.services.weather_service import get_weather
from app.services.web_search_service import TavilyError, search_web

# Sized for planning a whole trip in one turn: the local model tends to
# call save_itinerary_day once per round rather than batching.
MAX_TOOL_ROUNDS = 8

SYSTEM_PROMPT = (
    "You are trailmind, a well-traveled friend helping someone plan a trip. "
    "You can look up real, current details - prices, place names, addresses, "
    "opening hours - using a search tool before answering.\n\n"
    "Talk naturally, like you already know this stuff, not like you're "
    "describing a lookup you just did. Never say things like 'the knowledge "
    "base', 'the search results', 'according to the tool', or 'based on what "
    "I found' - just answer the question directly.\n\n"
    f"Your curated, verified guide covers: {', '.join(sorted(KNOWN_DESTINATIONS))}. "
    "For any of those, use search_destination_knowledge first and answer "
    "from what it returns - don't invent specifics (prices, names, "
    "addresses) that didn't come back from a search.\n\n"
    "Some destinations bundle more than one city (e.g. da_nang_hoi_an "
    "covers both Da Nang and Hoi An). When the question is about a "
    "specific one of those cities, pass its name as the `city` argument "
    "so the search doesn't mix in the wrong city's details.\n\n"
    "If a destination is outside your curated guide (not in the list above), "
    "or search_destination_knowledge comes back with no matching information "
    "even for a covered one, use search_web and/or your own general "
    "knowledge instead. Whenever you do this, your reply MUST start with a "
    "short flag making that explicit - e.g. 'That's outside my verified "
    "guide, but from a quick search...' or 'I don't have this in my guide, "
    "but from what I generally know...' - every single time, not just the "
    "first time in a conversation. This applies no matter how confident the "
    "search_web results or your own knowledge feel; only skip the flag for "
    "destinations in your curated guide list above.\n\n"
    "You can also look up real weather for any destination and date range "
    "with get_weather - it isn't limited to the destinations above. If the "
    "dates are too far out for a real forecast you'll get a typical/"
    "historical-average estimate instead of a live forecast - the tool "
    "result tells you which one it is ('forecast' vs 'historical_average'); "
    "say so plainly rather than presenting a historical average as if it "
    "were today's forecast."
)

ITINERARY_PROMPT = (
    "The itinerary and trip details only change when you call "
    "save_itinerary_day, delete_itinerary_day, update_trip_dates or "
    "update_trip_details. Never "
    "say you've added, updated, removed, extended or saved anything unless "
    "you called the matching tool in this turn and it succeeded - earlier "
    "messages in this conversation that mention updates don't show their "
    "tool calls, so don't take them as a pattern of just saying it.\n\n"
    "You can write to this trip's itinerary with save_itinerary_day - one "
    "call per day, and a full plan means a call for every day of the trip, "
    "not just some of them. When you propose a day-by-day plan, or the user asks to "
    "add/change something on a specific day, save it right away rather than "
    "asking first, then briefly mention in your reply that it's on their "
    "itinerary. Each call replaces that whole day, so when editing a day "
    "that already has a plan (see 'Itinerary so far' above), resend its "
    "existing items along with the change. Items are short labels shown "
    "side by side in a compact itinerary card - 2 to 5 words each, like "
    "'Train 09:10', 'Pena Palace', 'Dinner in Alfama' - never full "
    "sentences, and no 'Morning:'/'Afternoon:' prefixes. Put any longer "
    "explanation in your chat reply instead.\n\n"
    "To make the trip longer or shorter, or move it, call update_trip_dates "
    "first (e.g. adding a day 6 to a 5-day trip means extending the end "
    "date by one day, then saving day 6). delete_itinerary_day clears a "
    "single day and does not renumber the others. To shorten the trip when "
    "the user has said to drop what falls off the end, call "
    "update_trip_dates once with drop_days_past_end=true - no separate "
    "deletes needed - and tell the user which days were dropped. If they "
    "haven't said to drop those days, leave it false: the tool refuses "
    "and you should ask them first.\n\n"
    "Whenever the user mentions where they're going, how many people are "
    "travelling, or their budget, save it with update_trip_details right "
    "away (and their dates with update_trip_dates) - even if it's in "
    "passing, like 'two of us, Hoi An in November, about 2400 all in'. "
    "Only pass what they actually said; don't guess missing details."
)

SEARCH_KNOWLEDGE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_destination_knowledge",
        "description": (
            "Search the travel knowledge base for a destination. "
            f"Only covers: {', '.join(sorted(KNOWN_DESTINATIONS))}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "One of the known destination slugs.",
                },
                "query": {
                    "type": "string",
                    "description": "Free-text search query.",
                },
                "city": {
                    "type": "string",
                    "description": (
                        "Optional: narrow to one city within a destination that "
                        "bundles several (e.g. 'hoi_an' or 'da_nang' within "
                        "da_nang_hoi_an). Omit for single-city destinations."
                    ),
                },
            },
            "required": ["destination", "query"],
        },
    },
}

GET_WEATHER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Real forecast (dates within ~16 days) or typical historical-average "
            "weather (farther-out dates) for a destination or place - not limited "
            "to your curated guide's destinations, any real place name works."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": (
                        "One of the known destination slugs if it's in your guide, "
                        "otherwise any free-text place name (e.g. 'Paris')."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date, YYYY-MM-DD.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date, YYYY-MM-DD (inclusive).",
                },
                "city": {
                    "type": "string",
                    "description": (
                        "Optional: narrow to one city within a destination that "
                        "bundles several (e.g. 'hoi_an' or 'da_nang' within "
                        "da_nang_hoi_an)."
                    ),
                },
            },
            "required": ["destination", "start_date", "end_date"],
        },
    },
}

SEARCH_WEB_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Live web search. Use this only when search_destination_knowledge "
            "says a destination isn't covered, or comes back with no matching "
            "information for a covered one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text search query.",
                },
            },
            "required": ["query"],
        },
    },
}

SAVE_ITINERARY_DAY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_itinerary_day",
        "description": (
            "Save one day of the current trip's itinerary, replacing whatever "
            "that day had before."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "integer",
                    "description": "Day number within the trip, starting at 1.",
                },
                "title": {
                    "type": "string",
                    "description": "Short headline for the day, e.g. 'Sintra day trip'.",
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Short 2-5 word labels, not sentences, e.g. "
                        "['Train 09:10', 'Pena Palace', 'Dinner in Alfama']."
                    ),
                },
            },
            "required": ["day", "title", "items"],
        },
    },
}

DELETE_ITINERARY_DAY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delete_itinerary_day",
        "description": (
            "Clear one day of the current trip's itinerary. Other days keep "
            "their day numbers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "integer",
                    "description": "Day number to clear, starting at 1.",
                },
            },
            "required": ["day"],
        },
    },
}

UPDATE_TRIP_DATES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_trip_dates",
        "description": (
            "Set or change the current trip's start and end dates - to extend, "
            "shorten or move the trip. Refuses to shorten it while days past "
            "the new end still have saved plans, unless drop_days_past_end is true."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD."},
                "end_date": {"type": "string", "description": "YYYY-MM-DD, inclusive."},
                "drop_days_past_end": {
                    "type": "boolean",
                    "description": (
                        "Set true only when the user has explicitly said to drop "
                        "the days that fall past the new end - they're deleted in "
                        "the same call. Leave false otherwise."
                    ),
                },
            },
            "required": ["start_date", "end_date"],
        },
    },
}

UPDATE_TRIP_DETAILS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_trip_details",
        "description": (
            "Save the current trip's destinations, group size or budget. Pass "
            "only the details the user gave; anything left out stays as it is."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destinations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Every destination of the trip (replaces the current list). "
                        "Use a guide slug like 'da_nang_hoi_an' when it's in your "
                        "guide, otherwise the place name, e.g. 'Paris'."
                    ),
                },
                "party_size": {"type": "integer", "description": "Number of travellers."},
                "budget_planned": {
                    "type": "number",
                    "description": "Amount already planned/committed, as a plain number.",
                },
                "budget_total": {
                    "type": "number",
                    "description": "The user's total budget, as a plain number.",
                },
            },
        },
    },
}

TOOL_SCHEMAS = [SEARCH_KNOWLEDGE_SCHEMA, GET_WEATHER_SCHEMA, SEARCH_WEB_SCHEMA]
# Only offered when the turn belongs to a trip - there's nothing to write to otherwise.
TRIP_TOOL_SCHEMAS = TOOL_SCHEMAS + [
    SAVE_ITINERARY_DAY_SCHEMA,
    DELETE_ITINERARY_DAY_SCHEMA,
    UPDATE_TRIP_DATES_SCHEMA,
    UPDATE_TRIP_DETAILS_SCHEMA,
]
TRIP_TOOL_NAMES = {
    "save_itinerary_day",
    "delete_itinerary_day",
    "update_trip_dates",
    "update_trip_details",
}


def _run_search_destination_knowledge(arguments: dict, conn: psycopg.Connection | None) -> dict:
    try:
        snippets = search_destination_knowledge(
            destination=arguments.get("destination", ""),
            query=arguments.get("query", ""),
            city=arguments.get("city"),
            conn=conn,
        )
        if not snippets:
            return {
                "no_information_found": True,
                "message": (
                    "No matching information in the verified guide for this "
                    "query. Use search_web and/or your own general knowledge "
                    "instead, but make clear to the user that this isn't from "
                    "your verified guide."
                ),
            }
        return {"snippets": [dataclasses.asdict(s) for s in snippets]}
    except UnknownDestinationError as e:
        return {"error": str(e)}
    except (EmbeddingError, VectorStoreError) as e:
        return {"error": f"knowledge base temporarily unavailable: {e}"}


def _run_get_weather(arguments: dict) -> dict:
    try:
        start_date = datetime.date.fromisoformat(arguments.get("start_date", ""))
        end_date = datetime.date.fromisoformat(arguments.get("end_date", ""))
    except ValueError as e:
        return {"error": f"invalid date - expected YYYY-MM-DD: {e}"}

    try:
        result = get_weather(
            destination=arguments.get("destination", ""),
            start_date=start_date,
            end_date=end_date,
            city=arguments.get("city"),
        )
        return {**dataclasses.asdict(result), "start_date": str(result.start_date),
                "end_date": str(result.end_date)}
    except (UnknownCityError, ValueError) as e:
        return {"error": str(e)}
    except OpenMeteoError as e:
        return {"error": f"weather service temporarily unavailable: {e}"}


def _run_search_web(arguments: dict) -> dict:
    try:
        results = search_web(arguments.get("query", ""))
        return {"results": [dataclasses.asdict(r) for r in results]}
    except TavilyError as e:
        return {"error": f"web search temporarily unavailable: {e}"}


def _save_itinerary_day(
    arguments: dict, conn: psycopg.Connection, trip_id: int, user_message: str
) -> dict:
    saved = save_itinerary_day(
        conn,
        trip_id,
        day=arguments.get("day"),
        title=arguments.get("title", ""),
        items=arguments.get("items", []),
    )
    return {"saved": True, "day": saved.day_number, **saved.plan}


def _delete_itinerary_day(
    arguments: dict, conn: psycopg.Connection, trip_id: int, user_message: str
) -> dict:
    day = arguments.get("day")
    delete_itinerary_day(conn, trip_id, day)
    return {"deleted": True, "day": day}


_DROP_INTENT = re.compile(
    r"\b(drop|dropp\w*|remove\w*|delete\w*|cut|get rid|scrap\w*|ditch\w*|lose)\b", re.IGNORECASE
)


def _update_trip_dates(
    arguments: dict, conn: psycopg.Connection, trip_id: int, user_message: str
) -> dict:
    try:
        start_date = datetime.date.fromisoformat(arguments.get("start_date", ""))
        end_date = datetime.date.fromisoformat(arguments.get("end_date", ""))
    except ValueError as e:
        raise InvalidTripDatesError(f"invalid date - expected YYYY-MM-DD: {e}") from e

    wants_drop = arguments.get("drop_days_past_end") is True
    # Enforced here, not left to the prompt: live, gemma4 set the flag for a
    # plain "can we make the trip 3 days?" and deleted saved days. Missing a
    # real request is safe - the tool refuses and the model asks instead.
    drop_allowed = wants_drop and bool(_DROP_INTENT.search(user_message))
    try:
        trip, dropped = change_trip_dates(
            conn, trip_id, start_date, end_date, drop_days_past_end=drop_allowed
        )
    except InvalidTripDatesError as e:
        if wants_drop and not drop_allowed:
            raise InvalidTripDatesError(
                f"{e}. drop_days_past_end was ignored because the user hasn't "
                "explicitly said to drop those days - ask them to confirm first, "
                "don't retry"
            ) from e
        raise
    return {
        "updated": True,
        "start_date": str(trip.start_date),
        "end_date": str(trip.end_date),
        "days": trip_length(trip),
        "dropped_days": dropped,
    }


def _update_trip_details(
    arguments: dict, conn: psycopg.Connection, trip_id: int, user_message: str
) -> dict:
    trip = set_trip_details(
        conn,
        trip_id,
        destinations=arguments.get("destinations"),
        party_size=arguments.get("party_size"),
        budget_planned=arguments.get("budget_planned"),
        budget_total=arguments.get("budget_total"),
    )
    return {
        "updated": True,
        "destinations": trip.destinations,
        "party_size": trip.party_size,
        "budget_planned": trip.budget_planned,
        "budget_total": trip.budget_total,
    }


_TRIP_TOOL_RUNNERS = {
    "save_itinerary_day": _save_itinerary_day,
    "delete_itinerary_day": _delete_itinerary_day,
    "update_trip_dates": _update_trip_dates,
    "update_trip_details": _update_trip_details,
}


def _run_trip_tool(
    name: str,
    arguments: dict,
    conn: psycopg.Connection | None,
    trip_id: int | None,
    user_message: str,
) -> dict:
    if trip_id is None:
        return {"error": "no trip is selected, so there's no itinerary to change"}
    try:
        return _TRIP_TOOL_RUNNERS[name](arguments, conn, trip_id, user_message)
    except (InvalidItineraryDayError, InvalidTripDatesError, InvalidTripDetailsError) as e:
        return {"error": str(e)}
    except psycopg.Error as e:
        # Otherwise the aborted transaction would also break persisting
        # this turn's chat messages afterwards.
        conn.rollback()
        return {"error": f"itinerary temporarily unavailable: {e}"}


def _run_tool(
    name: str,
    arguments: dict,
    conn: psycopg.Connection | None,
    trip_id: int | None = None,
    user_message: str = "",
) -> dict:
    if name == "search_destination_knowledge":
        return _run_search_destination_knowledge(arguments, conn)
    if name == "get_weather":
        return _run_get_weather(arguments)
    if name == "search_web":
        return _run_search_web(arguments)
    if name in TRIP_TOOL_NAMES:
        return _run_trip_tool(name, arguments, conn, trip_id, user_message)
    return {"error": f"unknown tool '{name}'"}


def run_agent(
    user_message: str,
    llm: LLMClient | None = None,
    conn: psycopg.Connection | None = None,
    max_tool_rounds: int = MAX_TOOL_ROUNDS,
    trip_id: int | None = None,
) -> str:
    """Run one chat turn.

    If `trip_id` is given (requires `conn`): re-hydrates a compact trip-
    state summary and this trip's prior chat history into context (see
    CLAUDE.md "State model"), and persists this turn's user/assistant
    messages afterwards. Raises TripNotFoundError if the id doesn't
    exist - the caller (e.g. the API layer) decides how to surface that.
    Without `trip_id`, behaves exactly as before: a single stateless turn.
    """
    llm = llm or OllamaLLMClient()
    # The model has no other way to know the real date - without this it
    # guesses from training data and hallucinates stale/past dates for
    # get_weather (observed: asked "the next couple days", passed dates
    # from 2024). Computed per-call, not baked into the static
    # SYSTEM_PROMPT string, since it changes daily.
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Today's date is {datetime.date.today().isoformat()}."},
    ]

    tools = TOOL_SCHEMAS
    if trip_id is not None:
        trip = get_trip(conn, trip_id)
        for past in list_messages(conn, trip_id):
            messages.append({"role": past.role, "content": past.content})
        # After the history, not before: replayed replies like "I've updated
        # day 3" carry no tool calls, and with the itinerary rules buried
        # above them the local model imitated those and skipped saving.
        messages.append(
            {
                "role": "system",
                "content": f"Current trip state: {trip_summary(trip, list_days(conn, trip_id))}",
            }
        )
        messages.append({"role": "system", "content": ITINERARY_PROMPT})
        tools = TRIP_TOOL_SCHEMAS

    messages.append({"role": "user", "content": user_message})

    reply = None
    # Text the model writes alongside tool calls is often the substance of
    # the answer (e.g. introducing a plan while saving its days), with the
    # final turn just a short follow-up - so it's kept, not discarded.
    interim_text: list[str] = []
    for _ in range(max_tool_rounds):
        turn = llm.chat(messages, tools=tools)

        if not turn.tool_calls:
            final = (turn.content or "").strip()
            if not final and not interim_text:
                # gemma4 occasionally returns a completely empty turn; asking
                # again (the model samples) beats showing the user a blank reply.
                continue
            so_far = "\n\n".join(interim_text)
            # The model sometimes repeats its closing line in both turns.
            if final and final not in so_far:
                interim_text.append(final)
            reply = "\n\n".join(interim_text)
            break

        if turn.content and turn.content.strip():
            interim_text.append(turn.content.strip())

        messages.append(
            {
                "role": "assistant",
                "content": turn.content or "",
                "tool_calls": [
                    {"id": tc.id, "function": {"name": tc.name, "arguments": tc.arguments}}
                    for tc in turn.tool_calls
                ],
            }
        )
        for tc in turn.tool_calls:
            result = _run_tool(tc.name, tc.arguments, conn, trip_id, user_message)
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)}
            )

    if reply is None:
        # Exceeded max_tool_rounds without a final answer - infra-level
        # guard against an LLM stuck calling tools, not a policy decision
        # for it to make.
        reply = (
            "I wasn't able to put together an answer after checking the "
            "knowledge base a few times - could you rephrase your question?"
        )

    if trip_id is not None:
        append_message(conn, trip_id, "user", user_message)
        append_message(conn, trip_id, "assistant", reply)

    return reply
