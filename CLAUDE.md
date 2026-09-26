# CLAUDE.md — trailmind

## Purpose
An agentic chat app that plans trips incrementally (day by day) by
reasoning over tools, for destinations the user is actively planning
(currently: Da Nang/Hoi An, Bangkok, Almaty, Tokyo/Fuji/Hiroshima).

## Tools (v0)
- search_destination_knowledge(destination, query) -> ranked snippets + sources
  RAG-backed. Only covers the destinations listed above.

## State model
- Trip state lives in Supabase, not conversation history.
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

## Known constraints
- Destination knowledge base currently covers 4 destinations only.
- No flight/hotel search yet (v1).
- No subagent split yet (v2) — single agent only.