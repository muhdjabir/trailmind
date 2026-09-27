-- trailmind vector store: RAG chunks with metadata + embeddings.
-- Applied automatically on first container start via docker-entrypoint-initdb.d.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    destination TEXT NOT NULL,
    country TEXT,
    city TEXT,
    doc_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_file TEXT NOT NULL,
    section_path TEXT NOT NULL,
    chunk_id INT NOT NULL,
    text TEXT NOT NULL,
    word_count INT NOT NULL,
    possibly_orphaned BOOLEAN NOT NULL DEFAULT FALSE,
    embedding VECTOR(768) NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (destination, source_file, chunk_id)
);

-- destination stays the coverage/grouping key (KNOWN_DESTINATIONS,
-- corpus/<destination>/ layout); country/city are finer, optional
-- metadata for destinations that bundle multiple cities (e.g.
-- da_nang_hoi_an) so a query can be scoped to one city within it.
-- country isn't currently filtered on (no destination spans
-- countries yet) but is stored for completeness.

-- Metadata filtering (step 7: filter by destination before vector search).
CREATE INDEX IF NOT EXISTS idx_chunks_destination ON chunks (destination);

-- Finer filtering within a multi-city destination (step 14 finding: city conflation).
CREATE INDEX IF NOT EXISTS idx_chunks_destination_city ON chunks (destination, city);

-- Approximate nearest-neighbor search on cosine distance.
-- Fine to create even on a near-empty table at this corpus size;
-- revisit `lists`/HNSW params if the corpus grows significantly.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);

-- trailmind trip state (v1 step 15, CLAUDE.md "State model").
-- Local dev runs this against the same Postgres container as the
-- vector store above; DATABASE_URL is the swap point to point this
-- at real Supabase later (plain Postgres DDL, no Supabase-specific
-- features used yet, so no rewrite needed to move).

CREATE TABLE IF NOT EXISTS trips (
    id BIGSERIAL PRIMARY KEY,
    -- No auth yet - nullable and unenforced until a real user system
    -- exists, kept now so adding auth later isn't a breaking migration.
    user_id TEXT,
    name TEXT NOT NULL,
    -- Slugs from app.destinations.KNOWN_DESTINATIONS; not FK-constrained
    -- since that's an app-level list, not a DB table.
    destinations TEXT[] NOT NULL DEFAULT '{}',
    start_date DATE,
    end_date DATE,
    party_size INT,
    status TEXT NOT NULL DEFAULT 'draft',
    budget_planned NUMERIC,
    budget_total NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips (user_id);

CREATE TABLE IF NOT EXISTS itinerary_days (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    day_number INT NOT NULL,
    -- Kept as a JSONB blob for now rather than a normalized shape:
    -- the actual structure of a day's plan isn't defined until the
    -- tools that populate it (steps 17-20: weather/flights/hotels/
    -- save_itinerary_day) exist. Revisit once that shape is known.
    plan JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trip_id, day_number)
);
