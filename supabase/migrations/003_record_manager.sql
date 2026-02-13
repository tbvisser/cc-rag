ALTER TABLE documents ADD COLUMN content_hash TEXT;

-- Partial unique index: prevents same user uploading identical content
-- NULLs excluded so pre-migration rows don't conflict
CREATE UNIQUE INDEX idx_documents_user_content_hash
    ON documents(user_id, content_hash)
    WHERE content_hash IS NOT NULL;
