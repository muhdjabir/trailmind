from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, trips

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


app.include_router(chat.router)
app.include_router(trips.router)
