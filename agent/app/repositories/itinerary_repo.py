"""Per-day itinerary rows (`itinerary_days`, v1 step 20)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb


@dataclass
class ItineraryDay:
    id: int
    trip_id: int
    day_number: int
    plan: dict
    updated_at: datetime.datetime


def list_days(conn: psycopg.Connection, trip_id: int) -> list[ItineraryDay]:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT * FROM itinerary_days WHERE trip_id = %s ORDER BY day_number ASC",
            (trip_id,),
        )
        rows = cur.fetchall()
    return [ItineraryDay(**row) for row in rows]


def delete_day(conn: psycopg.Connection, trip_id: int, day_number: int) -> bool:
    """Returns False if that day had nothing saved."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM itinerary_days WHERE trip_id = %s AND day_number = %s",
            (trip_id, day_number),
        )
        deleted = cur.rowcount > 0
    conn.commit()
    return deleted


def delete_days_after(conn: psycopg.Connection, trip_id: int, last_day: int) -> list[int]:
    """Delete every day numbered above `last_day`; returns the deleted day numbers."""
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM itinerary_days WHERE trip_id = %s AND day_number > %s
            RETURNING day_number
            """,
            (trip_id, last_day),
        )
        deleted = sorted(row[0] for row in cur.fetchall())
    conn.commit()
    return deleted


def upsert_day(conn: psycopg.Connection, trip_id: int, day_number: int, plan: dict) -> ItineraryDay:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            INSERT INTO itinerary_days (trip_id, day_number, plan)
            VALUES (%s, %s, %s)
            ON CONFLICT (trip_id, day_number)
            DO UPDATE SET plan = EXCLUDED.plan, updated_at = now()
            RETURNING *
            """,
            (trip_id, day_number, Jsonb(plan)),
        )
        row = cur.fetchone()
    conn.commit()
    return ItineraryDay(**row)
