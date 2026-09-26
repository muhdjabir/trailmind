# agent

Python/FastAPI service: orchestration + RAG (see [CLAUDE.md](../CLAUDE.md)).

## Setup

```
python -m venv .venv
.venv/Scripts/activate      # Windows
source .venv/bin/activate   # macOS/Linux
pip install -r requirements-dev.txt
```

## Run tests

```
pytest
```

## Run the service

```
uvicorn app.main:app --reload
```
