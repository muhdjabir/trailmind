import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import run_agent
from app.llm import LLMError
from app.trips import Trip, TripNotFoundError, create_trip, get_trip, list_trips
from app.vector_store import VectorStoreError, get_connection

app = FastAPI(title="trailmind-agent")

# Local dev only: the Next.js dev server runs on a different origin/port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str
    trip_id: int | None = None


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        conn = get_connection()
    except VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        reply = run_agent(req.message, conn=conn, trip_id=req.trip_id)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    finally:
        conn.close()

    return ChatResponse(reply=reply)


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


class CreateTripRequest(BaseModel):
    name: str
    destinations: list[str] = []
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    party_size: int | None = None
    budget_planned: float | None = None
    budget_total: float | None = None


@app.post("/trips", response_model=TripResponse)
def create_trip_endpoint(req: CreateTripRequest) -> TripResponse:
    try:
        conn = get_connection()
    except VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
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
    finally:
        conn.close()

    return TripResponse.from_trip(trip)


@app.get("/trips", response_model=list[TripResponse])
def list_trips_endpoint() -> list[TripResponse]:
    try:
        conn = get_connection()
    except VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        trips = list_trips(conn)
    finally:
        conn.close()

    return [TripResponse.from_trip(t) for t in trips]


@app.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip_endpoint(trip_id: int) -> TripResponse:
    try:
        conn = get_connection()
    except VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        trip = get_trip(conn, trip_id)
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    finally:
        conn.close()

    return TripResponse.from_trip(trip)
