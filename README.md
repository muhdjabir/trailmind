# trailmind

An agentic chat app that plans trips incrementally by reasoning over tools.

See [CLAUDE.md](CLAUDE.md) for architecture, tool contracts, state model,
and conventions.

## Run it locally

Prerequisites: [Docker](https://www.docker.com/) and
[Ollama](https://ollama.com) running natively with the models pulled:

```
ollama pull nomic-embed-text
ollama pull gemma4
```

Then:

```
docker compose up -d --build
```

This starts Postgres+pgvector, the FastAPI agent (`localhost:8000`),
and the Next.js chat UI (`localhost:3000`) — Ollama stays native since
it's already running with models pulled. Code in `agent/app` and `web`
is bind-mounted, so edits hot-reload inside the containers.

First time only, load the corpus into the (empty) vector store from
inside the `agent` container:

```
docker compose exec agent python scripts/load_chunks_to_pg.py
```

(or run the full `fetch_corpus.py` -> `chunk_corpus.py` ->
`embed_corpus.py` -> `load_chunks_to_pg.py` pipeline first if you
haven't generated `corpus_chunks`/`corpus_embeddings` yet — see
`agent/corpus/README.md`.)

`docker compose down` stops everything; add `-v` to also drop the
Postgres data volume.
