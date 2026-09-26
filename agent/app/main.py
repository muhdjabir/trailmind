from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import run_agent
from app.llm import LLMError
from app.vector_store import VectorStoreError, get_connection

app = FastAPI(title="trailmind-agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        conn = get_connection()
    except VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        reply = run_agent(req.message, conn=conn)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    finally:
        conn.close()

    return ChatResponse(reply=reply)
