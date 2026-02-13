-- Add metadata column to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Create GIN indexes for JSONB containment queries
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin (metadata);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON chunks USING gin (metadata);

-- Replace search_chunks to accept optional metadata filter
CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding vector(1536),
    match_count int DEFAULT 5,
    match_threshold float DEFAULT 0.7,
    filter_user_id uuid DEFAULT NULL,
    filter_metadata jsonb DEFAULT NULL
)
RETURNS TABLE (
    id uuid, document_id uuid, content text,
    chunk_index int, metadata jsonb, similarity float
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT c.id, c.document_id, c.content, c.chunk_index, c.metadata,
           1 - (c.embedding <=> query_embedding) as similarity
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
      AND 1 - (c.embedding <=> query_embedding) > match_threshold
      AND (filter_metadata IS NULL OR c.metadata @> filter_metadata)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
