from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db_conn
from app.api.schemas import ChatMessageResponse, CreateTripRequest, TripResponse
from app.repositories.chat_history_repo import list_messages
from app.repositories.trips_repo import TripNotFoundError, create_trip, get_trip, list_trips

router = APIRouter()


@router.post("/trips", response_model=TripResponse)
def create_trip_endpoint(
    req: CreateTripRequest, conn: psycopg.Connection = Depends(get_db_conn)
) -> TripResponse:
    trip = create_trip(
        conn,
        name=req.name,
        destinations=req.destinations,
        start_date=req.start_date,
        end_date=req.end_date,
        party_size=req.party_size,
        budget_planned=req.budget_planned,
        budget_total=req.budget_total,
    )
    return TripResponse.from_trip(trip)


@router.get("/trips", response_model=list[TripResponse])
def list_trips_endpoint(conn: psycopg.Connection = Depends(get_db_conn)) -> list[TripResponse]:
    return [TripResponse.from_trip(t) for t in list_trips(conn)]


@router.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip_endpoint(
    trip_id: int, conn: psycopg.Connection = Depends(get_db_conn)
) -> TripResponse:
    try:
        trip = get_trip(conn, trip_id)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return TripResponse.from_trip(trip)


@router.get("/trips/{trip_id}/messages", response_model=list[ChatMessageResponse])
def list_trip_messages_endpoint(
    trip_id: int, conn: psycopg.Connection = Depends(get_db_conn)
) -> list[ChatMessageResponse]:
    try:
        get_trip(conn, trip_id)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return [ChatMessageResponse.from_message(m) for m in list_messages(conn, trip_id)]
