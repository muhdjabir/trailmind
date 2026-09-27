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
