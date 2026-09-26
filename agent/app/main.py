from fastapi import FastAPI

app = FastAPI(title="trailmind-agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
