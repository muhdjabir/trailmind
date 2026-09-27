"""Trip CRUD against the `trips` table (see CLAUDE.md "State model", v1 step 15a).

Create/list/get - "switching" between trips is just the frontend
re-fetching by id, no separate operation. Trip state, not conversation
history: this is the persistence layer step 16 will wire into the
agent's context.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import psycopg


class TripNotFoundError(Exception):
    """Raised when a trip id doesn't correspond to any row."""


@dataclass
class Trip:
    id: int
    user_id: str | None
    name: str
    destinations: list[str]
    start_date: datetime.date | None
    end_date: datetime.date | None
    party_size: int | None
    status: str
    budget_planned: float | None
    budget_total: float | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


def create_trip(
    conn: psycopg.Connection,
    name: str,
    user_id: str | None = None,
    destinations: list[str] | None = None,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    party_size: int | None = None,
    budget_planned: float | None = None,
    budget_total: float | None = None,
) -> Trip:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            INSERT INTO trips (
                user_id, name, destinations, start_date, end_date,
                party_size, budget_planned, budget_total
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                user_id,
                name,
                destinations or [],
                start_date,
                end_date,
                party_size,
                budget_planned,
                budget_total,
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return Trip(**row)


def list_trips(conn: psycopg.Connection, user_id: str | None = None) -> list[Trip]:
    where_clause = "WHERE user_id = %s" if user_id else ""
    params = [user_id] if user_id else []
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            f"SELECT * FROM trips {where_clause} ORDER BY created_at DESC",
            params,
        )
        rows = cur.fetchall()
    return [Trip(**row) for row in rows]


def update_trip_dates(
    conn: psycopg.Connection,
    trip_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Trip:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            UPDATE trips SET start_date = %s, end_date = %s, updated_at = now()
            WHERE id = %s
            RETURNING *
            """,
            (start_date, end_date, trip_id),
        )
        row = cur.fetchone()
    conn.commit()
    if row is None:
        raise TripNotFoundError(f"no trip with id {trip_id}")
    return Trip(**row)


def get_trip(conn: psycopg.Connection, trip_id: int) -> Trip:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
        row = cur.fetchone()
    if row is None:
        raise TripNotFoundError(f"no trip with id {trip_id}")
    return Trip(**row)
