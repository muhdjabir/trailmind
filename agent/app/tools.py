"""Agent-facing tools (see CLAUDE.md "Tools (v0)").

Tools return structured results or raise a typed error — never a
silent failure (empty list, swallowed exception). The agent decides
whether to retry, work around, or surface each error to the user;
this layer doesn't impose a retry/fallback policy of its own.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg

from app.destinations import KNOWN_DESTINATIONS
from app.retrieval import retrieve


class UnknownDestinationError(Exception):
    """Raised when asked about a destination outside the knowledge base's coverage."""


@dataclass
class Snippet:
    rank: int
    text: str
    source_url: str
    source_file: str
    section_path: str
    distance: float


def search_destination_knowledge(
    destination: str,
    query: str,
    top_k: int = 5,
    conn: psycopg.Connection | None = None,
) -> list[Snippet]:
    """Ranked snippets + sources for `query`, scoped to `destination`.

    RAG-backed; only covers the destinations in KNOWN_DESTINATIONS.
    Raises UnknownDestinationError, EmbeddingError, or VectorStoreError
    (never returns a silently-empty result) — the caller decides how
    to handle each.
    """
    if destination not in KNOWN_DESTINATIONS:
        raise UnknownDestinationError(
            f"'{destination}' is not covered by the knowledge base "
            f"(known destinations: {', '.join(sorted(KNOWN_DESTINATIONS))})"
        )

    results = retrieve(query, destination=destination, top_k=top_k, conn=conn)
    return [
        Snippet(
            rank=i + 1,
            text=r["text"],
            source_url=r["source_url"],
            source_file=r["source_file"],
            section_path=r["section_path"],
            distance=r["distance"],
        )
        for i, r in enumerate(results)
    ]
