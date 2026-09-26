# trailmind — Implementation List

## v0: Single agent + RAG tool
1. Assemble Da Nang/Hoi An corpus (5-10 blog/guide posts, relevant subreddit threads, tourism board pages, Wikivoyage)
2. Hand-chunk 2-3 docs manually to calibrate chunk quality (semantic-unit-first, not fixed-size)
3. Automate chunking based on calibration
4. Generate embeddings (text-embedding-3-small or bge-small-en local)
5. Stand up vector store (pgvector or FAISS) with metadata (source URL, destination, doc type)
6. Implement naive top-k retrieval
7. Add metadata filtering (destination) before vector search
8. Add reranking (bge-reranker-base or LLM call, top 20 → top 5)
9. Wrap retrieval as `search_destination_knowledge(destination, query)` tool
10. Stand up Python/FastAPI service with single agent + this tool
11. Build barebones Next.js chat UI, wire to FastAPI (unstyled OK)
12. Write CLAUDE.md into repo
13. Write 15-20 eval questions for Da Nang/Hoi An (known-good answers)
14. Score: retrieval quality (right chunk top-5?), answer quality, hallucination rate

**Checkpoint:** reasoning loop works end to end, no persistence yet.

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

## Conventions (see CLAUDE.md)
- pytest for Python tests
- Commits: `feat:` / `chore:` / `fix:`, kept short
- Tools return structured results or typed errors, never silent failure
- Agent decides retry/surface behavior per-situation, no fixed policy