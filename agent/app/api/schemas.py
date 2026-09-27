"""Request/response models for the HTTP API (controller-facing DTOs)."""

from __future__ import annotations

import datetime

from pydantic import BaseModel

from app.repositories.chat_history_repo import ChatMessage
from app.repositories.trips_repo import Trip
from app.services.trip_stats_service import TripStats


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


class WeatherStatsResponse(BaseModel):
    destination: str
    source: str  # "forecast" or "historical_average"
    avg_high_c: float
    avg_low_c: float
    total_precipitation_mm: float


class TripStatsResponse(BaseModel):
    trip_days: int | None
    days_planned: int
    open_days: list[int]
    budget_planned: float | None
    budget_total: float | None
    weather: WeatherStatsResponse | None
    weather_error: str | None

    @classmethod
    def from_stats(cls, stats: TripStats) -> "TripStatsResponse":
        weather = None
        if stats.weather is not None:
            weather = WeatherStatsResponse(
                destination=stats.weather_destination,
                source=stats.weather.source,
                avg_high_c=round(stats.weather.avg_high_c, 1),
                avg_low_c=round(stats.weather.avg_low_c, 1),
                total_precipitation_mm=round(stats.weather.total_precipitation_mm, 1),
            )
        return cls(
            trip_days=stats.trip_days,
            days_planned=stats.days_planned,
            open_days=stats.open_days,
            budget_planned=stats.budget_planned,
            budget_total=stats.budget_total,
            weather=weather,
            weather_error=stats.weather_error,
        )


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime.datetime

    @classmethod
    def from_message(cls, message: ChatMessage) -> "ChatMessageResponse":
        return cls(role=message.role, content=message.content, created_at=message.created_at)
