-- trailmind vector store: RAG chunks with metadata + embeddings.
-- Applied automatically on first container start via docker-entrypoint-initdb.d.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    destination TEXT NOT NULL,
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

-- Metadata filtering (step 7: filter by destination before vector search).
CREATE INDEX IF NOT EXISTS idx_chunks_destination ON chunks (destination);

-- Approximate nearest-neighbor search on cosine distance.
-- Fine to create even on a near-empty table at this corpus size;
-- revisit `lists`/HNSW params if the corpus grows significantly.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);
