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

from app.destinations import KNOWN_DESTINATIONS
from app.embeddings import EmbeddingError
from app.llm import LLMClient, OllamaLLMClient
from app.tools import UnknownDestinationError, search_destination_knowledge
from app.vector_store import VectorStoreError

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
    "addresses) that didn't come back from a search."
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
            conn=conn,
        )
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
) -> str:
    llm = llm or OllamaLLMClient()
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for _ in range(max_tool_rounds):
        turn = llm.chat(messages, tools=[TOOL_SCHEMA])

        if not turn.tool_calls:
            return turn.content or ""

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

    # Exceeded max_tool_rounds without a final answer - infra-level guard
    # against an LLM stuck calling tools, not a policy decision for it to make.
    return (
        "I wasn't able to put together an answer after checking the knowledge "
        "base a few times - could you rephrase your question?"
    )
