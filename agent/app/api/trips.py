from __future__ import annotations

import re

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_db_conn
from app.api.schemas import (
    ChatMessageResponse,
    CreateTripRequest,
    ItineraryDayResponse,
    TripResponse,
    TripStatsResponse,
)
from app.repositories.chat_history_repo import list_messages
from app.repositories.itinerary_repo import list_days
from app.repositories.trips_repo import TripNotFoundError, create_trip, get_trip, list_trips
from app.services.calendar_service import TripNotDatedError, build_trip_ics
from app.services.itinerary_service import day_date
from app.services.trip_stats_service import compute_trip_stats

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


@router.get("/trips/{trip_id}/itinerary", response_model=list[ItineraryDayResponse])
def list_trip_itinerary_endpoint(
    trip_id: int, conn: psycopg.Connection = Depends(get_db_conn)
) -> list[ItineraryDayResponse]:
    try:
        trip = get_trip(conn, trip_id)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return [
        ItineraryDayResponse(
            day_number=d.day_number,
            date=day_date(trip, d.day_number),
            title=d.plan.get("title", ""),
            items=d.plan.get("items", []),
            updated_at=d.updated_at,
        )
        for d in list_days(conn, trip_id)
    ]


@router.get("/trips/{trip_id}/stats", response_model=TripStatsResponse)
def get_trip_stats_endpoint(
    trip_id: int, conn: psycopg.Connection = Depends(get_db_conn)
) -> TripStatsResponse:
    try:
        stats = compute_trip_stats(conn, trip_id)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return TripStatsResponse.from_stats(stats)


@router.get("/trips/{trip_id}/itinerary.ics")
def export_trip_calendar_endpoint(
    trip_id: int, conn: psycopg.Connection = Depends(get_db_conn)
) -> Response:
    try:
        trip = get_trip(conn, trip_id)
        ics = build_trip_ics(trip, list_days(conn, trip_id))
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except TripNotDatedError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    filename = re.sub(r"[^A-Za-z0-9]+", "-", trip.name).strip("-").lower() or "trip"
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.ics"'},
    )
