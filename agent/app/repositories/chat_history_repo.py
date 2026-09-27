"""Chat history per trip (see CLAUDE.md "State model", v1 step 16).

Stores each turn's final user/assistant text so a trip's conversation
has continuity across turns - not the intra-turn tool-call round trips,
which are re-derived fresh by run_agent() each turn, not replayed.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import psycopg


@dataclass
class ChatMessage:
    id: int
    trip_id: int
    role: str
    content: str
    created_at: datetime.datetime


def append_message(conn: psycopg.Connection, trip_id: int, role: str, content: str) -> ChatMessage:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            INSERT INTO chat_messages (trip_id, role, content)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (trip_id, role, content),
        )
        row = cur.fetchone()
    conn.commit()
    return ChatMessage(**row)


def list_messages(conn: psycopg.Connection, trip_id: int) -> list[ChatMessage]:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT * FROM chat_messages WHERE trip_id = %s ORDER BY created_at ASC",
            (trip_id,),
        )
        rows = cur.fetchall()
    return [ChatMessage(**row) for row in rows]
