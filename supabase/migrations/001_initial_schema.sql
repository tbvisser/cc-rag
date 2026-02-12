-- Enable pgvector (for future modules)
CREATE EXTENSION IF NOT EXISTS vector;

-- Threads
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    openai_thread_id TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages (local cache - OpenAI is authoritative in M1)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    openai_message_id TEXT,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_threads_user_id ON threads(user_id);
CREATE INDEX idx_messages_thread_id ON messages(thread_id);

-- RLS
ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD own threads" ON threads
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can CRUD messages in own threads" ON messages
    FOR ALL USING (EXISTS (
        SELECT 1 FROM threads WHERE threads.id = messages.thread_id
        AND threads.user_id = auth.uid()
    ));
