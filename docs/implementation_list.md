# trailmind — Implementation List

## v0: Single agent + RAG tool
1. ✅ Assemble Da Nang/Hoi An corpus (5-10 blog/guide posts, relevant subreddit threads, tourism board pages, Wikivoyage)
   — 6 docs fetched (2 Wikivoyage + 4 blogs); Reddit threads skipped for now (scraping blocked, see `agent/scripts/fetch_corpus.py` notes)
2. ✅ Hand-chunk 2-3 docs manually to calibrate chunk quality (semantic-unit-first, not fixed-size)
   — see `agent/corpus/_calibration/`
3. ✅ Automate chunking based on calibration
   — `agent/app/chunking.py` + `agent/scripts/chunk_corpus.py`
4. ✅ Generate embeddings (text-embedding-3-small or bge-small-en local)
   — used `nomic-embed-text` via local Ollama instead (no API key/cost); `agent/app/embeddings.py`
5. ✅ Stand up vector store (pgvector or FAISS) with metadata (source URL, destination, doc type)
   — pgvector via `docker-compose.yml`, schema in `database/schema.sql`
6. ✅ Implement naive top-k retrieval
   — `agent/app/services/retrieval_service.py::retrieve()`
7. ✅ Add metadata filtering (destination) before vector search
   — done as part of step 5/6: `search()` filters by `destination` in the same query
8. Add reranking (bge-reranker-base or LLM call, top 20 → top 5)
9. ✅ Wrap retrieval as `search_destination_knowledge(destination, query)` tool
   — `agent/app/services/knowledge_service.py`; raises `UnknownDestinationError` for out-of-scope destinations, propagates typed embedding/DB errors unwrapped
10. ✅ Stand up Python/FastAPI service with single agent + this tool
    — `POST /chat` wired to `agent/app/services/chat_service.py::run_agent()`; LLM is local via Ollama (`gemma4:latest`, `agent/app/llm.py`), pluggable for Claude API later. Verified end-to-end: correctly grounds answers in retrieved chunks, and declines out-of-scope destinations (e.g. Bali) instead of hallucinating.
11. ✅ Build barebones Next.js chat UI, wire to FastAPI (unstyled OK)
    — `web/app/page.tsx`; single-turn per message (no server-side chat history yet). Verified end-to-end in a real browser via CORS-enabled `POST /chat`.
11a. ✅ Update the chat UI to match the "Trip Planner Chat v2" design mockup (desktop, "1a" variant)
    — Implemented from screenshots (the `claude_design` MCP referenced below wasn't
    available in this session - only a design-*system* sync tool was, which is
    explicitly scoped to a different workflow). `web/app/components/Sidebar.tsx`
    and `ItineraryPanel.tsx` are static demo chrome matching the mockup's sample
    "Lisbon & Porto" trip (trip list, budget header, day-by-day itinerary,
    hotel/stat cards - none of it wired to real data, since trip persistence is
    v1). The real, live piece is the center chat column: message list + input,
    restyled to match (dark bubble for user, red-dot avatar + markdown for
    assistant), still wired to the actual `POST /chat` backend. The mockup's
    3 suggestion chips are real and functional (they send their exact text).
    Verified end-to-end in a real browser: asked a real question through the
    new UI and got the same grounded, markdown-formatted answer as before;
    asked an out-of-scope one ("Porto") and got the correct honest refusal
    rendered in the new bubble style. Clean `next build` + `eslint`.
    — Mockup: Claude Design project at
    `https://claude.ai/design/p/77e572c5-2f7b-496f-b1c0-bc03235c2c17?file=Trip+Planner+Chat+v2.dc.html`.
    Import via the `claude_design` MCP (`https://api.anthropic.com/v1/design/mcp`,
    auth via `/design-login`). Primary file: `Trip Planner Chat v2.dc.html`;
    also read `_ds/modernist-471ec598-5fe0-4a6a-90e1-90b7245dcca1/_ds_bundle.js`,
    `_ds/modernist-471ec598-5fe0-4a6a-90e1-90b7245dcca1/styles.css`, and
    `support.js`, which it imports.
    Scope: desktop version only for now ("1a").
    Caveat: the agent's responses are still naive (plain markdown text,
    no structured itinerary/day-by-day data) — where the mockup implies
    UI elements the backend doesn't produce data for yet, note the gap
    rather than inventing fake data to fill it.
12. ✅ Write CLAUDE.md into repo
13. ✅ Write 15-20 eval questions for Da Nang/Hoi An (known-good answers)
    — `agent/eval/questions.yaml`, 20 questions across transport/food/shopping/accommodation/activities/nightlife/safety/money/practical/culture, plus 2 adversarial (out-of-scope destination, known-but-empty destination) and 2 that deliberately hit real cross-source inconsistencies in the corpus. (An informal spot-check while writing this had a bug in its own ad-hoc scoring and wrongly suggested a retrieval gap - see step 14, the real harness found 18/18 file-level retrieval hits.)
14. ✅ Score: retrieval quality (right chunk top-5?), answer quality, hallucination rate
    — `agent/scripts/run_eval.py`, results in `agent/eval/results/*.json` (gitignored). First full run:
    - **Retrieval: 18/18** (100%, file-level — expected doc landed in top-5 for every question).
    - **Answer quality: 35/50 key facts** (heuristic keyword coverage — approximate, not exact-match).
    - **Hallucination: found a real one.** q19 (Bangkok — a known destination with zero corpus chunks loaded) got a confident, plausible-sounding answer (specific dishes, general claims) instead of an honest "I don't have specifics" — the empty-tool-result signal wasn't strong enough to stop the LLM falling back on its own pretraining. q18 (Bali — fully unknown destination) correctly refused, since `UnknownDestinationError` is a much stronger, unambiguous signal than an empty list.
    - Manually reviewing the "misses" surfaced two more findings the heuristic score alone wouldn't show: q10 was actually a *good* answer (correctly said it didn't have a specific price rather than inventing one — the "miss" was just that pricing chunk not making top-5, not a hallucination); q04 revealed a real corpus-modeling gap — `da_nang_hoi_an` bundles two distinct cities under one destination, so a Hoi An-specific query has no metadata filter to exclude Da Nang content, and here it answered with a Da Nang shop instead of the Hoi An one.
    - **Findings status:**
      1. ✅ Empty-tool-result hallucination (q19) — `_run_tool` in `agent/app/services/chat_service.py`
         now returns `{"no_information_found": True, "message": ...}` instead of
         `{"snippets": []}` on a zero-result search, and `SYSTEM_PROMPT` explicitly
         tells the LLM this means "the knowledge base doesn't cover this, even for
         a known destination" rather than a cue to fall back on pretraining.
         Covered by `test_zero_snippets_fed_back_as_explicit_no_information_signal`
         in `agent/tests/test_chat_service.py`, and confirmed live via `run_eval.py --id
         q19`: `zero_snippets_returned=True` and the reply now honestly says it
         doesn't have specifics on Bangkok street food instead of inventing dishes.
      2. ✅ City-conflation within `da_nang_hoi_an` (q04) — added `country`/`city`
         columns to `chunks` (`database/schema.sql`), threaded an optional `city`
         filter through `search()`/`retrieve()`/`search_destination_knowledge()`,
         and tagged all 6 `corpus/da_nang_hoi_an/*.md` docs with `country: vietnam`
         + `city: da_nang`/`hoi_an` frontmatter. `destination` is unchanged as the
         coverage/grouping key (matches CLAUDE.md's tool contract); `city` only
         narrows within it, and the agent's tool schema/system prompt now tell the
         LLM to pass `city` when a question names one of a bundled destination's
         cities. Unit + integration tests added (`test_search_respects_city_filter_
         within_a_destination`, `test_city_argument_is_passed_through_to_retrieve`).
         Migrated the live dev DB (`ALTER TABLE ... ADD COLUMN country/city`, since
         the existing Postgres volume predates this change and schema.sql only
         applies on first init) and reran `chunk_corpus.py` → `embed_corpus.py` →
         `load_chunks_to_pg.py` for `da_nang_hoi_an` — 143 chunks reloaded, 83 tagged
         `city=da_nang`, 60 `city=hoi_an`. Confirmed via `run_eval.py --id q04`: the
         reply now names **Madam Khanh - The Banh Mi Queen** (a real Hoi An spot),
         not a Da Nang one. Full test suite (46 tests, including integration) passes
         against the live containers.

**Checkpoint:** ✅ v0 core loop done and scored, and both real findings
above are now fixed and verified (empty-tool-result signal + city
metadata filter, confirmed live via `run_eval.py` on q19/q04). Step 8
(reranking) is still open, but neither finding was blocking it — one
was a prompting/tool-result issue, the other a metadata granularity
issue, and reranking wouldn't have fixed either. Step 11a (UI mockup)
was a separate, presentation-only track that happened independently
of the retrieval/hallucination fixes.

## v1: Add tools + persistence
15. ✅ Add Supabase schema for trip state: `{ destinations, dates, budget, itinerary_by_day }`
    — needs to support multiple named trips per user (not just one), with
    metadata beyond the itinerary itself: name, dates, party size, status
    (e.g. "Draft itinerary"), and budget totals (planned vs. total) — see
    the sidebar trip list + header in the step 11a mockup.
    — `trips` + `itinerary_days` tables added to `database/schema.sql`,
    run locally against the same `trailmind-pg` container as the vector
    store (not a real Supabase project yet — `DATABASE_URL` is the swap
    point for that later; see CLAUDE.md "State model"). `trips` holds
    name, `destinations` (TEXT[] of `KNOWN_DESTINATIONS` slugs, not
    FK-constrained since that's an app-level list), dates, party size,
    status, and planned/total budget; `user_id` is nullable and
    unenforced for now (no auth exists yet) so it isn't a breaking
    migration once auth lands. `itinerary_days` FKs to `trips` (cascade
    delete) with a `(trip_id, day_number)` unique constraint and a JSONB
    `plan` column — kept unstructured deliberately, since the actual
    shape of a day's plan isn't known until the tools that populate it
    (steps 17-20) exist. Verified live: applied to the running container,
    inserted/read/cascade-deleted a sample trip + day successfully.
15a. ✅ Trip CRUD: create/list/switch between a user's trips
    — backs the sidebar's trip list and "New trip" button (currently
    static demo chrome, see step 11a).
    — `agent/app/repositories/trips_repo.py`: `create_trip`/`list_trips`/`get_trip` against
    the `trips` table; `get_trip` raises `TripNotFoundError` for an
    unknown id (matches the typed-error convention in CLAUDE.md/
    `knowledge_service.py` — a lookup by id has a real "doesn't exist"
    failure mode, unlike `list_trips`, where empty is just a normal
    result). "Switch" is just the frontend re-fetching by id — no
    separate endpoint. Wired to `POST /trips`, `GET /trips`,
    `GET /trips/{id}` in `agent/app/api/trips.py`.
    `user_id` filtering exists in `list_trips` but nothing sets it yet
    (no auth). Unit + integration tests in `tests/test_trips_repo.py` and
    `tests/test_main_trips.py`; also verified live against the running
    `trailmind-agent` container (create/list/404-on-missing all correct).
    — **UI wiring** (done after this and step 16 landed): `Sidebar.tsx`
    now fetches `GET /trips` and renders the real list instead of the
    mockup's static "Planning"/"Past" rows (that split isn't backed by
    any schema field, so it collapsed to one "Your trips" list); "+ New
    trip" is a small inline form (name only) that `POST`s and selects
    the new trip. `page.tsx` owns `selectedTripId` and passes it as
    `trip_id` on every `/chat` call, and the header now shows the
    selected trip's real name/status/budget instead of the mockup's
    "Lisbon & Porto". Selecting a trip also needed reading back its
    saved conversation, which nothing exposed yet, so added
    `GET /trips/{id}/messages` (404s on an unknown trip, same as
    `GET /trips/{id}`) backed by the existing `chat_history_repo.list_messages`.
    `ItineraryPanel` stays static - no itinerary-day endpoints exist yet
    (that's step 20). Verified in a real browser: created a trip via the
    inline form, asked it a question (correctly got the honest
    "no_information_found" refusal for empty-corpus Bangkok, per step
    14's fix), switched to a second trip and back, and the first trip's
    full prior exchange reloaded correctly from `chat_messages`.
16. ✅ Wire trip state read/write into agent context (compact summary per turn, not full history)
    — also needs the chat *history* itself persisted per trip (today
    every message is independent - see `agent/app/services/chat_service.py::run_agent()`),
    not just the derived trip-state summary.
    — `run_agent()` gained an optional `trip_id` param (still a single
    stateless turn without it, unchanged). With it: fetches the trip
    (`TripNotFoundError` propagates - caller decides, e.g. `POST /chat`
    now 404s on an unknown `trip_id`), injects a compact one-line-ish
    summary via new `app/services/trip_context.py::trip_summary()` as a system message
    (not the full row/itinerary - matches CLAUDE.md's "compact summary,
    not full conversation"), then loads and replays this trip's prior
    turns from a new `chat_messages` table (`app/repositories/chat_history_repo.py`) before
    the new user message. After the reply, persists this turn's
    user+assistant messages - deliberately just the final text of each
    turn, not the intra-turn tool-call round trips, which are re-derived
    fresh every turn rather than replayed. `POST /chat` takes an optional
    `trip_id`. Verified live: two chained `/chat` calls against a real
    trip correctly recalled a detail from the first turn in the second,
    and the injected trip summary showed up in the reply unprompted
    (mentioned "Da Nang and Hoi An" without being told); confirmed rows
    landed correctly in `chat_messages` and cascade-deleted with the
    trip. Unit tests in `tests/test_chat_service.py` (trip wiring, mocked) and
    `tests/test_trip_context.py`; integration tests in
    `tests/test_chat_history_repo.py`. 66 tests total pass.
16a. ✅ Refactor `agent/app/` into api/services/repositories layers
    — done before adding more tools (17-19), since `main.py`+`agent.py`
    were already mixing HTTP handling, orchestration, and DB access,
    and that would only get worse with weather/flights/hotels added on
    top. See CLAUDE.md "Conventions" for the layer breakdown. Pure
    move/rename/split, no behavior change, done as 3 commits (move
    repositories → move services, extracting `trip_summary()` out of
    the repository into a new `services/trip_context.py` → split
    `main.py` into `api/{chat,trips,schemas,deps}.py`), each verified
    with the full test suite and a live smoke test against the running
    `trailmind-agent` container before moving on.
17. ✅ Implement `get_weather(dest, dates)`
    — Open-Meteo (free, no API key - matches the project's zero-cost-local
    bias). `agent/app/open_meteo.py`: raw HTTP client, two endpoints
    (`/v1/forecast` for real forecasts ~16 days out, `/v1/archive` for
    past dates), `OpenMeteoError` typed like `EmbeddingError`/`LLMError`.
    `agent/app/services/weather_service.py::get_weather(destination,
    start_date, end_date, city=None)`: real forecast when `start_date` is
    within the ~16-day horizon; otherwise averages the same calendar
    range across the last 3 years as a "typical weather" estimate (trip
    dates are usually months out - a bare "forecast only" tool would be
    useless for most real questions). One failed year doesn't sink the
    whole average (`days_sampled` reports how many years actually
    landed); raises `OpenMeteoError` only if *all* years fail. Returns
    raw numbers, not a pre-written summary - the agent's reply
    synthesizes it, same as `search_destination_knowledge`.
    Coordinates are hardcoded per destination/city (`app/destinations.py::
    DESTINATION_COORDS`/`CITY_COORDS`/`destination_coords()`) rather than
    geocoded at request time - simple and reliable for the fixed,
    small `KNOWN_DESTINATIONS` set. `UnknownDestinationError` moved from
    `knowledge_service.py` into `destinations.py` (re-exported for
    backward compat) since it's now shared across two tools, not one.
    Wired into `chat_service.py` as a second tool alongside
    `search_destination_knowledge` (`TOOL_SCHEMAS` is now a list); the
    system prompt tells the model to say plainly which kind of answer
    it got (`forecast` vs `historical_average`) rather than presenting
    an average as if it were today's forecast.
    **Two real bugs found via live testing against the real local LLM**
    (gemma4, not just mocked unit tests) **and fixed:**
    1. The model has no notion of "today" and hallucinated stale dates
       from its training data (asked for "the next couple days", passed
       2024 dates) - fixed by injecting a `Today's date is ...` system
       message computed fresh per call (not baked into the static
       `SYSTEM_PROMPT` string, since it changes daily).
    2. The model redundantly echoed the destination name as `city` for
       single-city destinations (e.g. `city="bangkok"`), which the
       original strict `destination_coords()` rejected as an unknown
       city. Relaxed: `city` is only validated against a destination
       that actually has a per-city breakdown (`CITY_COORDS`); for a
       single-city destination it's silently ignored rather than
       erroring, since it's redundant input, not genuinely invalid.
       (Note: `search_destination_knowledge`'s `city` filter could have
       the same latent risk for a single-city destination - not fixed
       here, since Bangkok/Almaty have no corpus chunks yet either way
       and it wasn't observed failing; worth checking once they do.)
    Verified live against the running `trailmind-agent` container: a
    near-term Bangkok question got a real forecast; a far-future Almaty
    question correctly got - and was labeled as - a historical average;
    a Hoi An-specific question resolved to Hoi An's coordinates, not Da
    Nang's; an out-of-scope destination (Paris) correctly refused.
    Unit tests: `tests/test_open_meteo.py`, `tests/test_weather_service.py`,
    `tests/test_destinations.py`, plus tool-routing tests in
    `tests/test_chat_service.py`. 87 tests total pass.
18. Implement `search_flights(origin, dest, dates)` (Go service)
19. Implement `search_hotels(dest, dates, budget)` (Go service)
19a. Add a hotel/booking "hold" action (state, not just search)
    — the mockup's "Hold both" / "Show cheaper" buttons imply discrete
    mutations the backend must expose and apply, beyond a read-only search.
20. Implement `save_itinerary_day(day, plan)` → Supabase write
20a. Surface agent-initiated itinerary diffs to the UI (e.g. "Just added")
    — a way for the frontend to know *what changed* in the itinerary
    after a turn, not just fetch the new state wholesale.
21. Confirm agent picks correct tool per query type
22. Confirm itinerary state survives across turns/sessions
22a. Compute aggregated trip stats from itinerary state (e.g. total
    travel time, total stay cost, daily walking distance) — derived
    read, no new mutation; backs the mockup's stat cards.
22b. Generate contextual follow-up suggestions from current trip/itinerary
    state, replacing the mockup's static suggestion chips.
22c. Calendar export (ICS) generated from stored itinerary.
23. Expand destination corpus + eval set to remaining destinations (Bangkok, Almaty, Tokyo/Fuji/Hiroshima)

**Checkpoint:** agent correctly routes across all tools; state persists.
(15a, 19a, 20a, 22a-c added after reviewing the step 11a UI mockup —
they're what the sidebar/itinerary panel/stat cards/action buttons
imply the backend needs, beyond what was already listed above.)

## v2: Subagent split (do not start until v0/v1 seams are known)
24. Define `ResearchQuery` / `ResearchResult` handoff schema
25. Split into planner agent (itinerary, flights/hotels, Supabase writes) and research agent (RAG tool only)
26. Define failure-mode policy (planner behavior if research agent times out/fails)
27. Enforce ownership boundary: only planner writes to Supabase trip state

**Checkpoint:** handoff works; one agent's failure doesn't corrupt the other's output.

## Considered for later (not scheduled)
- **Web search for uncovered destinations.** Discussed and deliberately
  deferred: the RAG pipeline's value is the curated, calibrated corpus
  (controlled hallucination risk, reproducible answers you can write
  eval questions against per step 13/14) — live web search reintroduces
  the noise that corpus curation filtered out, plus cost/latency and
  non-reproducible results. If added, do it as a separate tool (e.g.
  `search_web(query)`) that the agent reaches for only when a
  destination isn't in `KNOWN_DESTINATIONS`, not blended into
  `search_destination_knowledge` — keep curated vs. live-web answers
  clearly separated rather than silently mixed.

## Conventions (see CLAUDE.md)
- pytest for Python tests
- Commits: `feat:` / `chore:` / `fix:`, kept short
- Tools return structured results or typed errors, never silent failure
- Agent decides retry/surface behavior per-situation, no fixed policy
