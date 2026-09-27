# agent

Python/FastAPI service: orchestration + RAG (see [CLAUDE.md](../CLAUDE.md)).

## Quickest way to run everything (Postgres + this service + web UI)

See the repo-root [README.md](../README.md) — `docker compose up -d --build`.
The rest of this file covers running things individually, which is
what you want for editing Python and running `pytest`.

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

## RAG pipeline (corpus -> chunks -> embeddings -> vector store)

Embeddings use a local [Ollama](https://ollama.com) server with
`nomic-embed-text` (no API key/cost). Requires `ollama serve` running
and the model pulled once: `ollama pull nomic-embed-text`.

The vector store is Postgres + pgvector, run via the repo-root
`docker-compose.yml` (`docker compose up -d`).

```
python scripts/fetch_corpus.py <url> --destination da_nang_hoi_an --doc-type blog
python scripts/chunk_corpus.py
python scripts/embed_corpus.py
python scripts/load_chunks_to_pg.py
```

See `corpus/README.md` for details on each step. `DATABASE_URL`
defaults to the local docker-compose credentials (`127.0.0.1`); inside
the `agent` container it's set to use the `postgres` service name
instead — override either via env var for anything else (e.g.
Supabase later).

## Agent

The chat loop lives in `app/services/chat_service.py::run_agent()`,
wired up at `POST /chat` (`{"message": "..."}` -> `{"reply": "..."}`,
`api/chat.py`). It's a
single-agent tool-calling loop over `search_destination_knowledge`:
the LLM decides when to call the tool, the tool result is fed back
into the conversation, and the LLM's next turn produces the final
answer (or explains an error/out-of-scope destination itself, rather
than the code hard-coding a response).

LLM backend is pluggable via the `app.llm.LLMClient` protocol.
`OllamaLLMClient` (default, `gemma4:latest`, overridable via
`OLLAMA_CHAT_MODEL`) is the only implementation for now — local, no
API key/cost, same server as embeddings (`OLLAMA_BASE_URL`, default
`http://localhost:11434`). An `AnthropicLLMClient` can be added later
against the same interface without touching `agent.py`.

```
ollama pull gemma4          # once
docker compose up -d        # pgvector
uvicorn app.main:app --reload
curl -X POST localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "best tailor shops in Hoi An?"}'
```
