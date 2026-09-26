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
defaults to the local docker-compose credentials; override it via
env var for anything else (e.g. Supabase later).
