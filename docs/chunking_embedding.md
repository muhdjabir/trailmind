# How trailmind's RAG pipeline works: chunking, embeddings, retrieval

This is a plain-language walkthrough of the RAG (retrieval-augmented
generation) pipeline that powers `search_destination_knowledge`, the
tool described in `CLAUDE.md`. It assumes no prior background in
embeddings or vector databases — every term is defined the first time
it's used, and every example is pulled from the real code and corpus
in this repo, not a hypothetical.

## 1. The big picture

trailmind's agent needs to answer questions like "where can I get a
custom suit made in Hoi An?" using real travel-guide content, not just
whatever the model already knows (which is often outdated or vague on
specific shop names and prices). CLAUDE.md describes the eventual tool
as:

> `search_destination_knowledge(destination, query) -> ranked snippets
> + sources`

To make that tool possible, we first need a way to search *inside* a
pile of scraped travel-guide pages and pull out the few paragraphs
that actually answer a given question — not the whole page, not
keyword matches, but the passages that are *about* the same thing the
user is asking about, even if they don't use the same words.

The pipeline that makes this possible has three stages, run once
ahead of time to build a searchable index, plus a fourth step that
runs live on every user question:

1. **Chunking** — break each scraped page into small, self-contained
   pieces ("chunks").
2. **Embedding** — turn each chunk's text into a list of numbers that
   captures its meaning.
3. **Storage** — save those chunks and their number-lists in a
   database built for searching by meaning (pgvector).
4. **Retrieval** — turn the user's question into the same kind of
   number-list, then ask the database "which stored chunks are
   closest in meaning to this?"

The rest of this doc walks through each stage using the actual code.

## 2. Chunking: breaking documents into meaningful pieces

### Why split documents up at all?

A raw travel guide page like the Hoi An Wikivoyage article is
thousands of words covering dozens of topics — getting there, where
to sleep, what to eat, where to shop. If the agent handed the *entire*
page to the language model every time someone asked a question, two
things would go wrong:

- **It wouldn't fit.** Language models can only read a limited amount
  of text at once (their "context window"). Feeding it every page for
  every destination on every turn would blow past that limit fast.
- **It would be imprecise.** Even if it fit, burying the one relevant
  paragraph about tailor shops inside 3,000 words about buses and
  hotels makes it harder for the model to find and use the right
  information, and wastes money/latency processing text that isn't
  needed.

So instead, each document gets split into "chunks" — self-contained
passages, each one small enough to be cheap to process and focused
enough that it's *about one thing*. Later, retrieval finds just the
1-5 chunks relevant to a specific question instead of the whole
document.

The tricky part is deciding *where* to cut. Cut too aggressively
(e.g., every paragraph) and you strand context — a list of tailor
shops means nothing without the warning paragraph next to it that
explains which ones are tourist traps. Cut too coarsely (e.g., whole
document = one chunk) and you're back to the "haystack" problem above.

### How the boundaries were decided: hand-chunking first

Before writing any chunking code, the project hand-annotated where a
human would cut three real documents — see
`agent/corpus/_calibration/`. Each `*.md` file there (e.g.
`hoi_an_wikivoyage.md`) is a table listing, section by section, where
to cut and why. `notes.md` distills the recurring decisions into
rules. This "calibrate by hand first" step matters because it's much
easier to notice that "list of tailor shops needs its warning
paragraph attached" by looking at real content than by guessing rules
in the abstract.

The Wikivoyage hand-chunking table is a good illustration of what
"good chunking" looks like across a single document: 39 chunks came
out of one article, and the notes conclude that for a heavily
sectioned source, headers alone get you about 80% of the way — the
real judgment calls are which small adjacent sections to merge
together.

### The actual rules, as implemented in `chunking.py`

`agent/app/chunking.py` (`chunk_document()`) encodes those calibration
findings as a sequence of passes:

**1. Strip noise before chunking anything.** Wikivoyage pages are full
of `[edit]` markers left over from the wiki software, and some blog
posts have affiliate-disclosure boilerplate. `strip_noise()` removes
lines matching known noise patterns (e.g. `[edit]`, stray `…`) and
drops whole paragraphs containing phrases like "affiliate link" before
any chunking happens, so noise never becomes its own (useless) chunk.

**2. Split on markdown headers first.** `split_into_sections()` walks
the document and starts a new section at every header (`#` through
`######`), tracking the heading hierarchy as it goes so each section
knows its full path, e.g. `Buy > Shopping > Markets`.

**3. Paragraph-fallback for header-less docs.** Some blog posts (like
`da_nang_midnightblue.md` in the calibration set) are loose narrative
prose with few or no real headers — trafilatura (the web-scraping
tool used in `fetch_corpus.py`) doesn't always recognize styled text
as a heading. If header-splitting produces just one giant section over
200 words, `paragraph_fallback_split()` kicks in and groups whole
paragraphs together up to ~200 words per group, never splitting a
paragraph in half.

**4. Merge small sections into their neighbor.** A tiny section (under
40 words) usually can't stand on its own as a meaningful chunk — its
meaning depends on the section next to it. `merge_small_sections()`
folds any such section into the previous one in reading order. This
directly encodes calibration rule 1, e.g. Wikivoyage's "Orientation"
(2 sentences) getting merged into "Understand", or "By shuttle bus"
and "By taxi" (each 1-3 sentences under "Get around") merging into one
chunk.

**5. Flag (don't auto-fix) orphaned content.** Sometimes a paragraph
ends up under the wrong header — a CMS or editing artifact. The
calibration notes mention a real case: a motorbike-rental aside about
the Hai Van Pass that was found sitting under a "Working Remotely"
header, where it clearly doesn't belong. `is_possibly_orphaned()`
implements a cheap heuristic for this: it pulls keywords out of the
section's heading path (using a synonym table — e.g. a "Sleep" header
implies words like "hotel," "hostel," "resort," since a Sleep section
rarely repeats the literal word "sleep") and checks whether *any* of
those keywords actually appear in the section's own text. If there's
zero overlap, the chunk is flagged `possibly_orphaned: true` for a
human to review later — the chunker doesn't try to guess where it
should actually go.

### A concrete before/after example

Here is the raw markdown for one real section of
`agent/corpus/da_nang_hoi_an/hoi-an-travel-guide-at-wikivoyage.md`,
under `Buy > Bespoke clothing`:

```
#### Bespoke clothing

[edit]
Hoi An is known as the centre for affordable custom-made clothing.
There are around 400 tailor shops in the city... Some strategies to
minimise your risk:

- Do not use recommendations from your accommodation or motorcycle
  drivers...
- Avoid Yaly's and Be Be. They are tourist traps...
- Order one thing at a time...
  [... 4 more bullets ...]

Tailor shops:

- Nathan Tailors, 127 Tran Hung Dao Street...
- Len Silk, 74 Tran Phu St...
  [... 4 more tailor listings ...]
```

After chunking, this becomes exactly one chunk with
`section_path = "Buy > Shopping > Bespoke clothing"`:

- The `[edit]` marker is gone (noise stripping).
- The risk-mitigation bullet list, the warning paragraph that frames
  it, *and* the actual tailor-shop listings all stay together as one
  chunk — this matches calibration rule 2 and 3 explicitly: "the
  risk-mitigation advice is meaningless without the tailor list it's
  warning about, and vice versa." Splitting per-bullet or separating
  the warning from the list would have destroyed exactly the context
  a question like "which tailors should I avoid in Hoi An" needs.
- It's long (roughly 250+ words) but wasn't split further, because
  size is treated as a *secondary* signal in this project — a chunk
  is fine being long if it's topically about one thing, and this one
  clearly is.

This is also the chunk that later gets correctly retrieved for the
query "best tailor shops for custom suits in Hoi An" — see Section 4.

## 3. Embeddings: turning text into coordinates

### What is an embedding, really?

An "embedding" is just a long list of numbers (a "vector") that a
model produces to represent the *meaning* of a piece of text. Think
of it like GPS coordinates, but instead of latitude/longitude placing
a location on a 2D map, an embedding places a piece of text at a point
in a space with hundreds of dimensions.

The property that makes this useful: text with similar meaning ends
up at points that are *close together* in that space, even if the
actual words are completely different. "custom suit tailor" and
"bespoke clothing shop" would land near each other, even though they
share almost no words, because the model that produces embeddings was
trained to understand meaning, not just match strings. "custom suit
tailor" and "bus schedule to Hue" would land far apart. This is what
lets retrieval later find the right chunk even when the user's exact
wording doesn't match the source document's wording.

### Why Ollama + nomic-embed-text

`agent/app/embeddings.py` generates embeddings using a local model
called `nomic-embed-text`, served by Ollama (a tool for running models
on your own machine). The implementation list
(`docs/implementation_list.md`, step 4) originally considered a paid
API option (`text-embedding-3-small`) but switched to this local
option instead — no API key, no per-request cost, and no data leaving
the machine, which matters for a project whose whole corpus is small
scraped web pages that get embedded repeatedly during development.

### What `embed_texts()` actually does

```python
def embed_texts(texts: list[str], model="nomic-embed-text",
                 base_url="http://localhost:11434") -> list[list[float]]:
```

Mechanically: it sends a batch of text strings in one HTTP POST to
Ollama's `/api/embed` endpoint (`http://localhost:11434` by default —
that's the Ollama server running on your own machine) and gets back
one embedding vector per input text, in the same order. Each vector
from `nomic-embed-text` has 768 numbers in it (that's the "dimension"
count referenced in the database schema, see Section 4).

Two things worth noting about the error handling, since CLAUDE.md
requires typed errors, not silent failure:
- If Ollama isn't running at all, `embed_texts()` raises a typed
  `EmbeddingError` with a hint ("is `ollama serve` running?") rather
  than letting a raw connection exception bubble up.
- If Ollama responds but the shape of the response doesn't match what
  was expected (wrong number of embeddings back), that also raises
  `EmbeddingError` instead of silently returning bad data.

`embed_corpus.py` calls this in batches of 16 chunks at a time over
every chunk produced by the chunking step, and writes the resulting
vectors alongside each chunk's text into
`corpus_embeddings/<destination>.jsonl`.

## 4. Vector store + retrieval

### What pgvector adds over a plain table

A normal Postgres column can store text or numbers, but there's no
built-in way to ask "which rows have a value *close to* this one" for
a 768-number vector — regular indexes (like B-trees) are built for
exact matches and ranges, not "nearest neighbor in 768-dimensional
space." The `vector` extension (pgvector) adds a new column type
(`VECTOR(768)` in `database/schema.sql`) plus operators and index
types built specifically for that kind of nearest-neighbor search.

### Cosine distance/similarity, intuitively

Going back to the coordinates analogy: if two embeddings are close
together in that 768-dimensional space, the text they represent is
similar in meaning. "Cosine similarity" is one specific way of
measuring how close two vectors are — instead of measuring straight-
line distance, it measures the *angle* between them (do they point in
roughly the same direction from the origin, regardless of length).
Two vectors pointing in nearly the same direction get a similarity
close to 1 (very similar); vectors pointing in unrelated directions
get a similarity close to 0.

`vector_store.py`'s `search()` function uses the `<=>` operator, which
is pgvector's **cosine distance** operator — the inverse idea: smaller
distance means more similar. That's why the SQL orders results
`ORDER BY embedding <=> %s` (ascending distance = most similar first)
and why the schema's index is built with `vector_cosine_ops`:

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);
```

That's an HNSW index (a graph-based structure for approximate
nearest-neighbor search) — it lets Postgres find "the closest vectors"
quickly without comparing the query against every single row in the
table one by one. At the current corpus size this doesn't matter much
for speed, but it's the mechanism that would keep search fast as the
corpus grows across the other three destinations in v1.

### Destination filtering

The schema also has a plain B-tree index on `destination`:

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_destination ON chunks (destination);
```

`search()` uses this by adding `WHERE destination = %s` to the query
*before* the similarity ordering, when a destination is given. This is
the "metadata filtering" from implementation-list step 7 — it narrows
the search to just Hoi An chunks (say) rather than also considering
similar-sounding content from Bangkok or Tokyo, combining an exact
filter with the approximate similarity search in one SQL query.

### `retrieve()`: tying it together

`agent/app/services/retrieval_service.py` is the function that CLAUDE.md's
`search_destination_knowledge` tool will eventually wrap:

```python
def retrieve(query, destination=None, top_k=5, conn=None):
    query_embedding = embed_texts([query])[0]
    ...
    return search(conn, query_embedding, destination=destination, top_k=top_k)
```

It does exactly two things: embed the user's free-text query using the
*same* embedding model used on the stored chunks (this matters —
comparing vectors from different embedding models is meaningless,
since each model has its own coordinate space), then hand that vector
to `search()` to find the closest stored chunks. No reranking happens
yet — it's a "naive top-k": whatever the `top_k` (default 5) closest
chunks are by cosine distance, in that order.

### The tailor-shop example, end to end

This is the concrete case that ties chunking and retrieval together:
querying `retrieve("best tailor shops for custom suits in Hoi An",
destination="da_nang_hoi_an")` correctly surfaces the
`Buy > Shopping > Bespoke clothing` chunk described in Section 2 — even
though the query says "tailor shops" and "custom suits" while the
source text says "bespoke clothing" and "tailor shops" (partial
overlap, but crucially the query and the chunk mean the same thing).
The embedding model places both pieces of text close together in
vector space because it understands they're about the same topic, not
because of exact keyword matching. This only works because that
chunk was kept as one coherent unit in Section 2's chunking step — if
the tailor list had been split away from its framing paragraph, or
buried inside a much larger "Buy" mega-chunk full of markets and ATMs,
the embedding for that chunk would represent a blurrier, less specific
topic and be less likely to rank at the top for this query.

## 5. How to run it yourself

Prerequisites:
- `ollama serve` running locally, with the embedding model pulled:
  `ollama pull nomic-embed-text`
- Local Postgres/pgvector running: `docker compose up -d` (from the
  repo root; picks up `database/schema.sql` automatically on first
  start)

Then, from `agent/`, run the pipeline scripts in order:

```bash
# 1. Scrape a page into corpus/<destination>/<slug>.md
python scripts/fetch_corpus.py <url> --destination da_nang_hoi_an --doc-type wikivoyage

# 2. Chunk every doc in corpus/<destination>/ into corpus_chunks/<destination>.jsonl
python scripts/chunk_corpus.py --destination da_nang_hoi_an

# 3. Embed every chunk into corpus_embeddings/<destination>.jsonl
python scripts/embed_corpus.py --destination da_nang_hoi_an

# 4. Load embedded chunks into the pgvector `chunks` table
python scripts/load_chunks_to_pg.py --destination da_nang_hoi_an
```

After that, `retrieve("your question", destination="da_nang_hoi_an")`
in `agent/app/services/retrieval_service.py` will query the loaded chunks directly.

## 6. What's not built yet

This pipeline is a mid-point snapshot, not the finished feature. Per
`docs/implementation_list.md`, still outstanding:

- **Step 8 — reranking.** Right now retrieval is "naive top-k": rank
  purely by cosine distance and return the top 5. A reranking step
  (e.g. `bge-reranker-base` or an LLM call scoring a wider top-20 down
  to top-5) isn't implemented yet. Manual spot-checks so far suggest
  retrieval quality is good without it, so it may end up being
  deprioritized in favor of step 9 below.
- **Step 9 — the `search_destination_knowledge` tool wrapper.**
  `retrieve()` exists as a plain Python function; it hasn't yet been
  wrapped as the actual callable tool the agent will invoke.
- **Step 10 — FastAPI/agent wiring.** The FastAPI service currently
  only has a `/health` endpoint (`agent/app/main.py`) — there's no
  agent loop or tool-calling wired up yet that would actually use this
  pipeline in a live chat.
