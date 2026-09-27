"""pgvector-backed chunk storage and similarity search.

Local dev DB is started via `docker compose up -d` (see
docker-compose.yml at repo root); schema lives in database/schema.sql.
"""

from __future__ import annotations

import os

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

DEFAULT_DATABASE_URL = "postgresql://trailmind:trailmind@127.0.0.1:5432/trailmind"


class VectorStoreError(Exception):
    """Typed error for vector store failures (connection, query, or shape issues)."""


def get_connection(database_url: str | None = None) -> psycopg.Connection:
    url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    try:
        conn = psycopg.connect(url, connect_timeout=5)
    except psycopg.OperationalError as e:
        raise VectorStoreError(
            f"could not connect to postgres at {url} "
            f"(is `docker compose up -d` running?): {e}"
        ) from e
    register_vector(conn)
    return conn


def upsert_chunks(conn: psycopg.Connection, records: list[dict]) -> int:
    if not records:
        return 0
    with conn.cursor() as cur:
        for r in records:
            cur.execute(
                """
                INSERT INTO chunks (
                    destination, country, city, doc_type, source_url, source_file,
                    section_path, chunk_id, text, word_count,
                    possibly_orphaned, embedding, embedding_model
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (destination, source_file, chunk_id) DO UPDATE SET
                    country = EXCLUDED.country,
                    city = EXCLUDED.city,
                    doc_type = EXCLUDED.doc_type,
                    source_url = EXCLUDED.source_url,
                    section_path = EXCLUDED.section_path,
                    text = EXCLUDED.text,
                    word_count = EXCLUDED.word_count,
                    possibly_orphaned = EXCLUDED.possibly_orphaned,
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model
                """,
                (
                    r["metadata"]["destination"],
                    r["metadata"].get("country"),
                    r["metadata"].get("city"),
                    r["metadata"]["doc_type"],
                    r["metadata"]["source_url"],
                    r["source_file"],
                    r["section_path"],
                    r["chunk_id"],
                    r["text"],
                    r["word_count"],
                    r["possibly_orphaned"],
                    r["embedding"],
                    r["embedding_model"],
                ),
            )
    conn.commit()
    return len(records)


def search(
    conn: psycopg.Connection,
    query_embedding: list[float],
    destination: str | None = None,
    city: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    conditions = []
    filters: list[str] = []
    if destination:
        conditions.append("destination = %s")
        filters.append(destination)
    if city:
        conditions.append("city = %s")
        filters.append(city)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    # embedding is referenced twice (SELECT distance + ORDER BY), so the
    # vector param is duplicated to match the two placeholders below.
    # Wrapped in Vector(): outside a column-typed context (e.g. this raw
    # `<=>` in a SELECT list), psycopg can't infer "vector" from a plain
    # list and postgres fails to resolve the operator overload.
    vec = Vector(query_embedding)
    params = [vec] + filters + [vec, top_k]

    query = f"""
        SELECT destination, country, city, doc_type, source_url, source_file, section_path,
               chunk_id, text, word_count,
               embedding <=> %s AS distance
        FROM chunks
        {where_clause}
        ORDER BY embedding <=> %s
        LIMIT %s
    """
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()
