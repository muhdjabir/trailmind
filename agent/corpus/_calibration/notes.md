# Chunking calibration notes (for step 3 automation)

Derived from hand-chunking 3 docs (see sibling files). Rules for the
automated chunker, roughly in priority order:

1. **Headers are a starting point, not the answer.** Split on H2/H3
   by default, but:
   - Merge a sibling section into its neighbor if it's too short to
     stand alone (~<50 words) and shares query intent (e.g. Wikivoyage
     "Orientation" into "Understand"; "By shuttle bus" + "By taxi").
   - Split a single header's content further if it covers genuinely
     distinct query intents (e.g. "By bus" split per origin city —
     Da Nang / Hue / other — since a user asking about one origin
     shouldn't retrieve the others).

2. **Lists stay attached to their framing sentence, as one chunk.**
   A bullet list (landmarks, restaurants, tailor shops) plus the
   paragraph introducing/qualifying it is one semantic unit. Do not
   chunk per-bullet — individual bullets lose the shared context that
   makes them answer the query (e.g. tailor risk-mitigation advice is
   meaningless without the tailor list it warns about).

3. **Numbered "listicle" items (blog "N things to do") are naturally
   1 chunk = 1 item.** No merging or splitting needed — the author
   already did the semantic chunking via H3 headings.

4. **Don't trust physical position blindly — watch for orphaned
   content.** A paragraph can sit under the wrong header (editing/CMS
   artifact). If a paragraph's topic doesn't match its enclosing
   header, chunk it separately rather than let it dilute that
   section's embedding. (Seen once: a motorbike-rental aside about
   Hai Van Pass dropped under "Working Remotely.")

5. **Strip non-content before chunking, don't chunk it:**
   - Wikivoyage `[edit]` markers
   - Affiliate-disclosure boilerplate
   - Extraction artifacts (stray `…`, stripped widget placeholders)

6. **Size is a secondary signal, not primary.** Most good chunks land
   ~60–400 words. Only intervene on size when a chunk would otherwise
   be too small to carry standalone meaning (merge) or genuinely
   spans multiple unrelated topics (split) — a chunk being long is
   fine if it's topically single (e.g. the Wikivoyage motorbike-safety
   section, or a full "day trips" list).

7. **Carry doc-level metadata down to chunk level**, plus a
   `section_path` (e.g. `Get in > By bus > From Da Nang`) per chunk.
   `doc_type` in particular should inform reranking later — prefer
   `wikivoyage`/`tourism_board` chunks for prices/logistics, `blog`
   chunks for anecdote-driven recommendations.

## What this means for step 3 (automated chunking)

A pure fixed-size or pure header-split strategy will get most of this
right by volume, but will silently mis-chunk the cases in rules 2–4.
Given the corpus is small (6 docs), it's worth a chunker that:
- splits on headers first,
- applies a min-word-count merge pass on adjacent siblings,
- flags (for manual review, not auto-fix) any chunk where a list
  appears without a preceding intro sentence, or where paragraph
  topic keywords diverge sharply from the enclosing header — both are
  cheap heuristics that would have caught rules 2 and 4 above without
  needing an LLM call per chunk.
