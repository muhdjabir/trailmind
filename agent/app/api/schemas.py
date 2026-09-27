"""Request/response models for the HTTP API (controller-facing DTOs)."""

from __future__ import annotations

import datetime

from pydantic import BaseModel

from app.repositories.chat_history_repo import ChatMessage
from app.repositories.trips_repo import Trip


class ChatRequest(BaseModel):
    message: str
    trip_id: int | None = None


class ChatResponse(BaseModel):
    reply: str


class CreateTripRequest(BaseModel):
    name: str
    destinations: list[str] = []
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    party_size: int | None = None
    budget_planned: float | None = None
    budget_total: float | None = None


class TripResponse(BaseModel):
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

    @classmethod
    def from_trip(cls, trip: Trip) -> "TripResponse":
        return cls(**trip.__dict__)


class ItineraryDayResponse(BaseModel):
    day_number: int
    # Derived from the trip's start_date, never stored - None while the
    # trip's dates are still open.
    date: datetime.date | None
    title: str
    items: list[str]
    updated_at: datetime.datetime


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime.datetime

    @classmethod
    def from_message(cls, message: ChatMessage) -> "ChatMessageResponse":
        return cls(role=message.role, content=message.content, created_at=message.created_at)
