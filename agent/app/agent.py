"""Single-agent reasoning loop over the search_destination_knowledge tool.

CLAUDE.md v2 note: no subagent split yet - this is the one agent.
Tool failures aren't caught-and-hidden; they're fed back into the
conversation as the tool result, so the LLM's own next turn decides
how to explain it to the user (matches CLAUDE.md's "agent decides
retry/surface, no fixed policy").
"""

from __future__ import annotations

import dataclasses
import json

import psycopg

from app.repositories.chat_history_repo import append_message, list_messages
from app.destinations import KNOWN_DESTINATIONS
from app.embeddings import EmbeddingError
from app.llm import LLMClient, OllamaLLMClient
from app.tools import UnknownDestinationError, search_destination_knowledge
from app.repositories.trips_repo import get_trip, trip_summary
from app.repositories.vector_store_repo import VectorStoreError

MAX_TOOL_ROUNDS = 3

SYSTEM_PROMPT = (
    "You are trailmind, a well-traveled friend helping someone plan a trip. "
    "You can look up real, current details - prices, place names, addresses, "
    "opening hours - using a search tool before answering.\n\n"
    "Talk naturally, like you already know this stuff, not like you're "
    "describing a lookup you just did. Never say things like 'the knowledge "
    "base', 'the search results', 'according to the tool', or 'based on what "
    "I found' - just answer the question directly.\n\n"
    f"You only have detailed info on: {', '.join(sorted(KNOWN_DESTINATIONS))}. "
    "If asked about anywhere else, say plainly that you don't have details on "
    "it rather than guessing. Don't invent specifics (prices, names, "
    "addresses) that didn't come back from a search.\n\n"
    "Some destinations bundle more than one city (e.g. da_nang_hoi_an "
    "covers both Da Nang and Hoi An). When the question is about a "
    "specific one of those cities, pass its name as the `city` argument "
    "so the search doesn't mix in the wrong city's details.\n\n"
    "If a search comes back with no matching information, that means the "
    "knowledge base doesn't cover this specific thing - even for a "
    "destination you otherwise know about. Say so honestly instead of "
    "filling the gap with plausible-sounding details from your own general "
    "knowledge."
)

TOOL_SCHEMA = {
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


def _run_tool(name: str, arguments: dict, conn: psycopg.Connection | None) -> dict:
    if name != "search_destination_knowledge":
        return {"error": f"unknown tool '{name}'"}

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
                    "No matching information in the knowledge base for this "
                    "query. Do not answer from general knowledge - tell the "
                    "user plainly that you don't have specifics on this."
                ),
            }
        return {"snippets": [dataclasses.asdict(s) for s in snippets]}
    except UnknownDestinationError as e:
        return {"error": str(e)}
    except (EmbeddingError, VectorStoreError) as e:
        return {"error": f"knowledge base temporarily unavailable: {e}"}


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
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if trip_id is not None:
        trip = get_trip(conn, trip_id)
        messages.append(
            {"role": "system", "content": f"Current trip state: {trip_summary(trip)}"}
        )
        for past in list_messages(conn, trip_id):
            messages.append({"role": past.role, "content": past.content})

    messages.append({"role": "user", "content": user_message})

    reply = None
    for _ in range(max_tool_rounds):
        turn = llm.chat(messages, tools=[TOOL_SCHEMA])

        if not turn.tool_calls:
            reply = turn.content or ""
            break

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
            result = _run_tool(tc.name, tc.arguments, conn)
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
