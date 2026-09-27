# CLAUDE.md — trailmind

## Purpose
An agentic chat app that plans trips incrementally (day by day) by
reasoning over tools, for destinations the user is actively planning
(currently: Da Nang/Hoi An, Bangkok, Almaty, Tokyo/Fuji/Hiroshima).

## Tools
- search_destination_knowledge(destination, query, city=None) -> ranked
  snippets + sources. RAG-backed. Only covers the destinations listed
  above; `city` narrows within a destination that bundles several (e.g.
  "hoi_an" within da_nang_hoi_an). Vector store: Postgres + pgvector
  (not FAISS) — schema in `database/schema.sql`.
- get_weather(destination, start_date, end_date, city=None) -> avg
  high/low/precipitation. Open-Meteo (free, no API key). Real forecast
  within ~16 days out; a historical average over the last 3 years for
  farther-out dates (labeled as such — never presented as a live
  forecast). Not limited to the destinations above: a known destination
  uses hardcoded coordinates (`app/destinations.py`); anything else is
  geocoded from the free-text name via Open-Meteo's geocoding API.
- search_web(query) -> ranked web results. Tavily (`TAVILY_API_KEY` env
  var, via `.env` locally — gitignored, never commit it). Fallback only:
  reached for when search_destination_knowledge raises
  `UnknownDestinationError` or returns `no_information_found` — kept
  separate, never blended into the curated tool. Every reply built on
  search_web or general knowledge (instead of the curated guide) must
  open with an explicit flag that it isn't from the verified guide —
  this is a strengthened, MUST-level instruction in `SYSTEM_PROMPT`
  (chat_service.py); a softer phrasing was tried first and the local
  model just skipped it.
- save_itinerary_day(day, title, items) -> replaces one day of the
  current trip's itinerary (`itinerary_days`). Only offered when the
  turn has a `trip_id`, which `run_agent` supplies itself - never an
  LLM argument. Writes immediately, no confirmation step. `items` are
  short 2-5 word labels, not sentences. Bad day/shape raises
  `InvalidItineraryDayError` (fed back to the model).
- delete_itinerary_day(day) -> clears one day; other days keep their
  numbers (no renumbering).
- update_trip_dates(start_date, end_date, drop_days_past_end=false) ->
  sets/moves/extends/shortens the trip. Day dates are derived from
  `start_date`, so moving needs no itinerary rewrite. Shortening past
  saved days is refused (`InvalidTripDatesError`) unless
  `drop_days_past_end` is set, which deletes them in the same call.
  That flag is only honored when the user's message this turn says to
  drop/remove/delete/cut them (`_DROP_INTENT` in chat_service.py) -
  enforced in code because gemma4 set it for a plain "can we make it 3
  days?". A missed match is safe: the tool refuses and the model asks.
- All three trip tools are only offered on trip-scoped turns.
- search_destination_knowledge raises `UnknownDestinationError` for a
  destination outside `KNOWN_DESTINATIONS` (defined once in
  `app/destinations.py`, shared across tools — not redefined per tool).
  get_weather does not raise this — see above.

## LLM & embeddings backend
- Chat LLM and embeddings both run locally via Ollama by default
  (`gemma4` for chat, `nomic-embed-text` for embeddings) — no API key
  or per-call cost. Configurable via `OLLAMA_BASE_URL` /
  `OLLAMA_CHAT_MODEL` env vars.
- The chat LLM is swappable: `app.llm.LLMClient` is a Protocol: any
  provider (e.g. a future Claude API client) can implement it without
  touching `app/services/chat_service.py`.

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
- `run_agent(..., trip_id=...)` does this: injects the trip's compact
  summary (`app/services/trip_context.py::trip_summary()`, including an
  outline of saved itinerary days) plus its prior chat history
  (`chat_messages` table, `app/repositories/chat_history_repo.py`) into
  context, then persists this turn's user/assistant messages after
  replying. Without `trip_id` it's a single stateless turn, unchanged
  from before.
- Order matters: the trip summary and itinerary rules go *after* the
  replayed history, right before the new user message. History stores
  only final text (no tool calls), and with the rules placed first the
  local model imitated past "I've updated day 3" replies instead of
  calling save_itinerary_day.

## Tool error handling
- Tools return structured results or a typed error — never silent failure.
- No fixed retry/surface policy: the agent decides whether to retry,
  work around, or surface the error to the user, based on the situation.

## Conventions
- Python/FastAPI owns orchestration + RAG. Go owns tool microservices.
  Next.js is presentation only.
- `agent/app/` layering: `api/` (FastAPI routers + request/response DTOs
  + the `get_db_conn` dependency) → `services/` (business logic:
  `chat_service.py` is the tool-calling loop, `knowledge_service.py`/
  `retrieval_service.py` back the RAG tool, `trip_context.py` formats
  trip state for the LLM) → `repositories/` (plain DB-access functions
  taking an explicit `conn`, no ORM/base-repository class). `llm.py`/
  `embeddings.py` (external Ollama clients), `destinations.py` (domain
  constant), and `chunking.py` (build-time corpus tool, not part of the
  runtime request path) sit outside this stack at the top level.
- Python tests: pytest.
- Commit messages: prefix with feat:/chore:/fix:, keep them short — no
  verbose bodies unless a decision genuinely needs explaining.
- Agent replies must sound like a person answering, not a system
  narrating its own retrieval — never phrases like "the knowledge
  base states", "based on the search results", "according to the
  tool". Keep this in mind when editing `SYSTEM_PROMPT` in
  `app/services/chat_service.py`.

## Known constraints
- Destination knowledge base currently covers 4 destinations only.
- No flight/hotel search yet (v1).
- No subagent split yet (v2) — single agent only.
- Reddit blocks automated fetching (`scripts/fetch_corpus.py` gets a
  403/login wall) — Reddit sources need a manual workaround (paste
  text or PDF export) rather than the normal fetch flow.