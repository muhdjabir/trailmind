from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db_conn
from app.api.schemas import ChatRequest, ChatResponse
from app.llm import LLMError
from app.repositories.trips_repo import TripNotFoundError
from app.services.chat_service import run_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, conn: psycopg.Connection = Depends(get_db_conn)) -> ChatResponse:
    try:
        reply = run_agent(req.message, conn=conn, trip_id=req.trip_id)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except TripNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return ChatResponse(reply=reply)
