-- Migration: Hybrid Search & Reranking
-- Add full-text search column to chunks and keyword search function

-- Add auto-computed tsvector column for full-text search
ALTER TABLE chunks
ADD COLUMN fts tsvector
GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- GIN index for fast full-text search
CREATE INDEX idx_chunks_fts ON chunks USING gin(fts);

-- Keyword search function using Postgres full-text search
CREATE OR REPLACE FUNCTION search_chunks_keyword(
    query_text text,
    match_count int DEFAULT 20,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    chunk_index int,
    metadata jsonb,
    rank float
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
        ts_rank_cd(c.fts, websearch_to_tsquery('english', query_text))::float AS rank
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE
        (filter_user_id IS NULL OR d.user_id = filter_user_id)
        AND c.fts @@ websearch_to_tsquery('english', query_text)
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;
