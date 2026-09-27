"""FastAPI dependencies shared across routers."""

from __future__ import annotations

from collections.abc import Generator

import psycopg
from fastapi import HTTPException

from app.repositories.vector_store_repo import VectorStoreError, get_connection


def get_db_conn() -> Generator[psycopg.Connection, None, None]:
    """Open one Postgres connection for the request, close it after.

    Centralizes the get_connection()/HTTPException(503)/close() dance
    that used to be duplicated in every endpoint.
    """
    try:
        conn = get_connection()
    except VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        yield conn
    finally:
        conn.close()
