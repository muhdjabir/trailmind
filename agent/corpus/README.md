# corpus

Raw source documents for the RAG knowledge base, one subdirectory per
destination (`da_nang_hoi_an/`, `bangkok/`, `almaty/`, `tokyo_fuji_hiroshima/`).

Populate with:

```
python scripts/fetch_corpus.py <url> [<url> ...] --destination da_nang_hoi_an --doc-type blog
```

Each file is markdown with a YAML frontmatter block (`source_url`,
`destination`, `doc_type`, `title`, `fetched_date`) followed by the
cleaned page text. This is the input to the chunking step, not the
chunked/embedded output.

## Chunking

```
python scripts/chunk_corpus.py [--destination da_nang_hoi_an]
```

Splits each doc into semantic-unit chunks per the rules calibrated in
`_calibration/notes.md`, and writes `corpus_chunks/<destination>.jsonl`
(gitignored — regenerate anytime from the committed corpus).

## Embedding

Requires a local [Ollama](https://ollama.com) server (`ollama serve`)
with the `nomic-embed-text` model pulled (`ollama pull nomic-embed-text`) —
no API key or per-call cost.

```
python scripts/embed_corpus.py [--destination da_nang_hoi_an]
```

Reads `corpus_chunks/`, writes `corpus_embeddings/<destination>.jsonl`
(gitignored) with a 768-dim `embedding` vector added to each chunk
record.

## Vector store (pgvector)

Requires the local Postgres container from the repo-root
`docker-compose.yml`: `docker compose up -d` (schema in
`database/schema.sql` is applied automatically on first start).

```
python scripts/load_chunks_to_pg.py [--destination da_nang_hoi_an]
```

Upserts `corpus_embeddings/` into the `chunks` table (unique on
`destination, source_file, chunk_id`, so reruns are idempotent).
Query it with `app.vector_store.search(conn, query_embedding,
destination=...)`, which does cosine-distance nearest-neighbor with
optional metadata filtering by destination.

## The tool: `search_destination_knowledge`

```python
from app.tools import search_destination_knowledge

snippets = search_destination_knowledge("da_nang_hoi_an", "best tailor shops", top_k=5)
```

This is the `search_destination_knowledge(destination, query)` tool
from CLAUDE.md — embeds the query, searches the vector store scoped
to `destination`, and returns a ranked list of `Snippet(rank, text,
source_url, section_path, distance)`. Raises `UnknownDestinationError`
for a destination outside `app.destinations.KNOWN_DESTINATIONS`
(never a silent empty result); embedding/DB failures raise the typed
errors from `app.embeddings` / `app.vector_store` unwrapped, per
CLAUDE.md's tool error-handling convention.
