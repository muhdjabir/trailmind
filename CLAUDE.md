# CLAUDE.md — trailmind

## Purpose
An agentic chat app that plans trips incrementally (day by day) by
reasoning over tools, for destinations the user is actively planning
(currently: Da Nang/Hoi An, Bangkok, Almaty, Tokyo/Fuji/Hiroshima).

## Tools (v0)
- search_destination_knowledge(destination, query) -> ranked snippets + sources
  RAG-backed. Only covers the destinations listed above.
  Vector store: Postgres + pgvector (not FAISS) — schema in `database/schema.sql`.

## LLM & embeddings backend
- Chat LLM and embeddings both run locally via Ollama by default
  (`gemma4` for chat, `nomic-embed-text` for embeddings) — no API key
  or per-call cost. Configurable via `OLLAMA_BASE_URL` /
  `OLLAMA_CHAT_MODEL` env vars.
- The chat LLM is swappable: `app.llm.LLMClient` is a Protocol: any
  provider (e.g. a future Claude API client) can implement it without
  touching `app/agent.py`.

## Local dev
- `docker compose up -d --build` runs the whole stack: Postgres
  +pgvector, the FastAPI agent, and the Next.js UI. Ollama runs
  natively (not containerized) — start it and pull the two models
  above before bringing the stack up.
- Agent/web code is bind-mounted, so edits hot-reload inside the
  containers.

## State model
- Trip state lives in Supabase, not conversation history. Local dev
  runs this against the same Postgres container as the vector store
  (`trips` + `itinerary_days` in `database/schema.sql`); `DATABASE_URL`
  is the swap point to point at real Supabase later.
- Shape: { destinations, dates, budget, itinerary_by_day }
- Each turn re-hydrates a compact summary of trip state into context,
  not the full conversation.

## Tool error handling
- Tools return structured results or a typed error — never silent failure.
- No fixed retry/surface policy: the agent decides whether to retry,
  work around, or surface the error to the user, based on the situation.

## Conventions
- Python/FastAPI owns orchestration + RAG. Go owns tool microservices.
  Next.js is presentation only.
- Python tests: pytest.
- Commit messages: prefix with feat:/chore:/fix:, keep them short — no
  verbose bodies unless a decision genuinely needs explaining.
- Agent replies must sound like a person answering, not a system
  narrating its own retrieval — never phrases like "the knowledge
  base states", "based on the search results", "according to the
  tool". Keep this in mind when editing `SYSTEM_PROMPT` in
  `app/agent.py`.

## Known constraints
- Destination knowledge base currently covers 4 destinations only.
- No flight/hotel search yet (v1).
- No subagent split yet (v2) — single agent only.
- Reddit blocks automated fetching (`scripts/fetch_corpus.py` gets a
  403/login wall) — Reddit sources need a manual workaround (paste
  text or PDF export) rather than the normal fetch flow.