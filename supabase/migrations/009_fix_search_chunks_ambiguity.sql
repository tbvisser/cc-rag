-- Migration: Fix search_chunks function ambiguity
-- Problem: Migrations 004 and 008 created two overloads of search_chunks with
-- different signatures (4-param vs 5-param), causing PostgREST to return
-- "300 Multiple Choices" on every RPC call.
-- Fix: Drop both overloads and create a single definitive version.

-- Drop both overloads
DROP FUNCTION IF EXISTS search_chunks(vector(1536), int, float, uuid);
DROP FUNCTION IF EXISTS search_chunks(vector(1536), int, float, uuid, jsonb);

-- Create single definitive version with all parameters
CREATE FUNCTION search_chunks(
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    match_threshold float DEFAULT 0.3,
    filter_user_id uuid DEFAULT NULL,
    filter_metadata jsonb DEFAULT NULL
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
        AND (filter_metadata IS NULL OR c.metadata @> filter_metadata)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
