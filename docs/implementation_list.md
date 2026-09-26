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
   — `agent/app/retrieval.py::retrieve()`
7. ✅ Add metadata filtering (destination) before vector search
   — done as part of step 5/6: `search()` filters by `destination` in the same query
8. Add reranking (bge-reranker-base or LLM call, top 20 → top 5)
9. ✅ Wrap retrieval as `search_destination_knowledge(destination, query)` tool
   — `agent/app/tools.py`; raises `UnknownDestinationError` for out-of-scope destinations, propagates typed embedding/DB errors unwrapped
10. ✅ Stand up Python/FastAPI service with single agent + this tool
    — `POST /chat` wired to `agent/app/agent.py::run_agent()`; LLM is local via Ollama (`gemma4:latest`, `agent/app/llm.py`), pluggable for Claude API later. Verified end-to-end: correctly grounds answers in retrieved chunks, and declines out-of-scope destinations (e.g. Bali) instead of hallucinating.
11. ✅ Build barebones Next.js chat UI, wire to FastAPI (unstyled OK)
    — `web/app/page.tsx`; single-turn per message (no server-side chat history yet). Verified end-to-end in a real browser via CORS-enabled `POST /chat`.
12. ✅ Write CLAUDE.md into repo
13. ✅ Write 15-20 eval questions for Da Nang/Hoi An (known-good answers)
    — `agent/eval/questions.yaml`, 20 questions across transport/food/shopping/accommodation/activities/nightlife/safety/money/practical/culture, plus 2 adversarial (out-of-scope destination, known-but-empty destination) and 2 that deliberately hit real cross-source inconsistencies in the corpus. (An informal spot-check while writing this had a bug in its own ad-hoc scoring and wrongly suggested a retrieval gap - see step 14, the real harness found 18/18 file-level retrieval hits.)
14. ✅ Score: retrieval quality (right chunk top-5?), answer quality, hallucination rate
    — `agent/scripts/run_eval.py`, results in `agent/eval/results/*.json` (gitignored). First full run:
    - **Retrieval: 18/18** (100%, file-level — expected doc landed in top-5 for every question).
    - **Answer quality: 35/50 key facts** (heuristic keyword coverage — approximate, not exact-match).
    - **Hallucination: found a real one.** q19 (Bangkok — a known destination with zero corpus chunks loaded) got a confident, plausible-sounding answer (specific dishes, general claims) instead of an honest "I don't have specifics" — the empty-tool-result signal wasn't strong enough to stop the LLM falling back on its own pretraining. q18 (Bali — fully unknown destination) correctly refused, since `UnknownDestinationError` is a much stronger, unambiguous signal than an empty list.
    - Manually reviewing the "misses" surfaced two more findings the heuristic score alone wouldn't show: q10 was actually a *good* answer (correctly said it didn't have a specific price rather than inventing one — the "miss" was just that pricing chunk not making top-5, not a hallucination); q04 revealed a real corpus-modeling gap — `da_nang_hoi_an` bundles two distinct cities under one destination, so a Hoi An-specific query has no metadata filter to exclude Da Nang content, and here it answered with a Da Nang shop instead of the Hoi An one.
    - **Not fixed yet** — these are findings step 14 was designed to produce, not resolved:
      1. Empty-tool-result hallucination (q19): likely fix is making `_run_tool`'s zero-snippets response an explicit "no information found" signal instead of a bare empty list, plus a system-prompt tweak.
      2. City-conflation within `da_nang_hoi_an` (q04): would need a finer-grained metadata field (e.g. `city`) to filter on, beyond the current `destination` grouping.

**Checkpoint:** ✅ v0 core loop done and scored. Both real findings above
are unresolved — worth fixing before or alongside step 8 (reranking),
since reranking wouldn't fix either one (one's a prompting/tool-result
issue, the other's a metadata granularity issue).

## v1: Add tools + persistence
15. Add Supabase schema for trip state: `{ destinations, dates, budget, itinerary_by_day }`
16. Wire trip state read/write into agent context (compact summary per turn, not full history)
17. Implement `get_weather(dest, dates)`
18. Implement `search_flights(origin, dest, dates)` (Go service)
19. Implement `search_hotels(dest, dates, budget)` (Go service)
20. Implement `save_itinerary_day(day, plan)` → Supabase write
21. Confirm agent picks correct tool per query type
22. Confirm itinerary state survives across turns/sessions
23. Expand destination corpus + eval set to remaining destinations (Bangkok, Almaty, Tokyo/Fuji/Hiroshima)

**Checkpoint:** agent correctly routes across all tools; state persists.

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
