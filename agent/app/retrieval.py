"""Naive top-k retrieval: embed a query, search the vector store.

This is the piece CLAUDE.md's search_destination_knowledge(destination,
query) tool will wrap: given free-text, return ranked snippets + sources.
No reranking yet (step 8) — top-k by cosine distance only.
"""

from __future__ import annotations

import psycopg

from app.embeddings import embed_texts
from app.vector_store import get_connection, search


def retrieve(
    query: str,
    destination: str | None = None,
    city: str | None = None,
    top_k: int = 5,
    conn: psycopg.Connection | None = None,
) -> list[dict]:
    """Ranked snippets + sources for `query`, optionally scoped to `destination`

    and, within it, to one `city` (for destinations that bundle several,
    e.g. da_nang_hoi_an)."""
    query_embedding = embed_texts([query])[0]

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        return search(conn, query_embedding, destination=destination, city=city, top_k=top_k)
    finally:
        if owns_conn:
            conn.close()
