-- Migration: Improve retrieval quality
-- Switch from IVFFlat to HNSW index (better recall for small datasets)
-- Update search_chunks function defaults

-- Drop IVFFlat index
DROP INDEX IF EXISTS idx_chunks_embedding;

-- Create HNSW index (better recall at all dataset sizes, no training needed)
CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Update search_chunks function with lower default threshold and higher match count
CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    match_threshold float DEFAULT 0.3,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    chunk_index int,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.content,
        c.chunk_index,
        c.metadata,
        1 - (c.embedding <=> query_embedding) as similarity
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE
        (filter_user_id IS NULL OR d.user_id = filter_user_id)
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
