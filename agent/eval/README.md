# eval

Step 13 of `docs/implementation_list.md`: 20 hand-written questions for
Da Nang/Hoi An with known-good answers, grounded in the actual corpus
(`corpus/da_nang_hoi_an/`) — not invented facts.

## Format (`questions.yaml`)

Each entry has:
- `question` / `destination` — the input to `search_destination_knowledge`
  (or `run_agent`, for a full end-to-end eval).
- `expected_source_files` — which corpus doc(s) the right chunk should
  come from. Empty for the two adversarial questions (q18, q19), where
  no chunk should be relevant at all.
- `key_facts` — short facts the final answer should contain. Not exact
  strings to match verbatim; check that the *substance* is there.
- `must_not_invent` (adversarial questions only) — the kind of specific
  detail (names, prices) the answer must NOT fabricate.
- `notes` — flags corpus inconsistencies between sources (q06, q16) or
  explains why a question is adversarial (q18, q19).

## What this maps to for step 14 scoring

- **Retrieval quality**: for each question, call
  `search_destination_knowledge(destination, question)` and check
  whether any returned snippet's `source_url`/`source_file` matches
  `expected_source_files`.
- **Answer quality**: run the question through `run_agent()` and check
  whether the reply mentions the substance of each `key_facts` entry.
- **Hallucination rate**: for q18/q19, check the reply doesn't contain
  specifics that aren't in the corpus (q18: no Bali content at all,
  since it's outside `KNOWN_DESTINATIONS`; q19: no fabricated Bangkok
  specifics, since `bangkok` is known but has zero chunks loaded).

Two questions (q06, q16) deliberately hit real inconsistencies between
sources in the corpus (e.g. one blog recommends a tailor shop that the
Wikivoyage doc calls a tourist trap). These aren't bugs — they're
useful checks for whether the agent uncritically blends conflicting
sources or handles the tension reasonably.

No scoring harness yet — that's the rest of step 14, once there's a
reason to compare runs (e.g. before/after adding reranking, step 8).
