# Session Handoff - Module 2 (Sub-Plans 2.1-2.4 Complete)

## Current State

Module 1 fully complete. Module 2 has 4 of 5 sub-plans done. **Only Sub-Plan 2.5 (Realtime Ingestion Status) remains.**

The full RAG pipeline is implemented end-to-end:
**Upload → Store in Supabase Storage → Chunk text → Embed via OpenAI → Store in pgvector → Retrieve on chat → Inject into system prompt → Stream response with source citations**

---

## What's Been Done

### Module 1: App Shell + Observability - COMPLETE
- React + Vite + Tailwind + shadcn/ui frontend
- Python + FastAPI backend (no SDK - httpx REST calls to Supabase)
- Supabase Auth (ES256 JWT), threads, messages with RLS
- SSE streaming chat with OpenAI-compatible API
- Auth middleware supports JWKS for ES256

### Sub-Plan 2.1: Schema Refactor + Chat Completions Migration - COMPLETE
- Dropped OpenAI thread/message IDs from schema
- Created documents + chunks tables with pgvector
- Created `search_chunks()` postgres function for vector similarity
- Migrated from Responses API to Chat Completions API
- Added `llm_service.py` for generic OpenAI-compatible completions
- Message history now managed in DB, sent to LLM each request

### Sub-Plan 2.2: Document Storage + Upload UI - COMPLETE
- `storage_service.py` - Supabase Storage upload/delete/download via httpx
- `documents.py` routes - POST (upload), GET (list), GET (single), DELETE
- `document.py` model - Pydantic DocumentResponse
- Frontend: Documents page with drag-and-drop upload, document list with status badges
- Header navigation between Chat and Documents views
- Auto-creates `documents` storage bucket on first upload

### Sub-Plan 2.3: Chunking + Embedding Pipeline - COMPLETE
- `chunking_service.py` - Recursive character splitter (paragraphs → lines → sentences → words)
- `embedding_service.py` - OpenAI-compatible async embedding with batch support
- `ingestion_service.py` - Orchestrates: download → extract text → chunk → embed → store
- Text extraction for .txt, .md, .csv, .json, .pdf (via pypdf)
- Background processing via FastAPI BackgroundTasks after upload
- Document status transitions: pending → processing → completed/failed

### Sub-Plan 2.4: Retrieval Tool + RAG Integration - COMPLETE
- `retrieval_service.py` - Embed query → vector search → enrich with filenames
- `format_context()` - Formats chunks with source labels and relevance scores
- Updated `chat.py` - Retrieves relevant chunks before LLM call, injects into system prompt
- Graceful fallback: if retrieval fails or no documents, uses base prompt
- SSE sends `sources` metadata before streaming content
- Frontend shows source document badges above assistant responses

---

## What's NOT Done

### Sub-Plan 2.5: Realtime Ingestion Status (✅ Simple)
- [ ] Create `frontend/src/hooks/useDocumentStatus.ts` - Supabase Realtime subscription
- [ ] Update `DocumentList.tsx` for live status updates (pending → processing → completed)
- [ ] Visual indicators: spinner for processing, checkmark for done, X for failed
- [ ] No page refresh needed - status updates via websocket

**Note:** The visual indicators (spinner, checkmark, X) already exist in `DocumentList.tsx` via the `StatusBadge` component. The remaining work is subscribing to Supabase Realtime so the status updates without manual refresh.

---

## File Structure

```
backend/
├── app/
│   ├── config.py                       # Supabase, LLM, embedding, chunking env vars
│   ├── main.py                         # FastAPI app - health, chat, documents routers
│   ├── api/
│   │   ├── middleware/auth.py          # ES256 JWT auth (JWKS from Supabase)
│   │   └── routes/
│   │       ├── chat.py                 # Thread CRUD + RAG-enhanced message streaming
│   │       ├── documents.py            # Document upload/list/delete + background ingestion
│   │       └── health.py
│   ├── models/
│   │   ├── chat.py                     # Thread/Message Pydantic models
│   │   └── document.py                 # DocumentResponse Pydantic model
│   └── services/
│       ├── chunking_service.py         # Recursive character text splitter
│       ├── embedding_service.py        # OpenAI-compatible async embeddings
│       ├── ingestion_service.py        # Full pipeline: download → chunk → embed → store
│       ├── llm_service.py              # Generic Chat Completions (OpenAI/OpenRouter/Ollama)
│       ├── retrieval_service.py        # Query embedding + vector search + format context
│       ├── storage_service.py          # Supabase Storage upload/delete/download
│       ├── supabase_service.py         # All DB CRUD via httpx REST (threads/messages/documents/chunks)
│       └── openai_service.py           # DEPRECATED - legacy, to be removed
├── requirements.txt                    # fastapi, httpx, openai, pypdf, python-multipart, etc.
└── .env.example

frontend/
└── src/
    ├── App.tsx                         # Routes: /, /documents, /login, /signup
    ├── pages/
    │   ├── Chat.tsx                    # Chat page with sidebar + messages
    │   ├── Documents.tsx               # Document upload + list page
    │   ├── Login.tsx
    │   └── Signup.tsx
    ├── components/
    │   ├── layout/
    │   │   ├── Header.tsx              # Nav links: Chat, Documents + sign out
    │   │   └── Sidebar.tsx             # Thread list for chat
    │   ├── chat/
    │   │   ├── MessageList.tsx         # Messages + source badges + streaming
    │   │   └── MessageInput.tsx
    │   ├── documents/
    │   │   ├── DocumentUpload.tsx      # Drag-and-drop upload zone
    │   │   └── DocumentList.tsx        # Document list with StatusBadge component
    │   ├── auth/
    │   │   └── AuthGuard.tsx
    │   └── ui/ (button, input, card)
    ├── hooks/
    │   ├── useChat.ts                  # Chat state + streaming + sources
    │   ├── useSSE.ts                   # SSE stream parser (content + sources)
    │   └── useDocuments.ts             # Document CRUD hook
    ├── contexts/
    │   └── AuthContext.tsx             # Supabase Auth context
    └── lib/
        ├── api.ts                      # apiFetch + apiStreamUrl helpers
        ├── supabase.ts                 # Supabase client
        └── utils.ts                    # cn() utility

supabase/
└── migrations/
    ├── 001_initial_schema.sql          # threads, messages + RLS
    └── 002_byo_retrieval.sql           # documents, chunks, vector search function
```

---

## How to Start Servers

```bash
# Backend (terminal 1)
cd backend
venv\Scripts\activate      # Windows CMD
# source venv/Scripts/activate  # Git Bash
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm run dev
```

---

## Environment

- **Supabase Project:** rpbkbslaedifbktwswpa
- **Supabase CLI:** C:\Users\TBVis\supabase-cli\supabase.exe
- **Backend:** Python 3.14, FastAPI, port 8000
- **Frontend:** React + Vite, port 5173
- **Full plan:** `.agent/plans/2.module2-byo-retrieval.md`

### Required .env (backend/.env)
```
SUPABASE_URL=https://rpbkbslaedifbktwswpa.supabase.co
SUPABASE_SERVICE_KEY=<service-role-key>
SUPABASE_JWT_SECRET=<jwt-secret>
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=<your-key>
LLM_MODEL=gpt-4o-mini
EMBEDDING_API_KEY=<your-openai-key>
```

### Required .env (frontend/.env)
```
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://rpbkbslaedifbktwswpa.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
```

---

## Known Issues
- `frontend/src/lib/api.ts` has a pre-existing TS error (HeadersInit indexing) - doesn't affect runtime
- `backend/app/services/openai_service.py` is deprecated/unused - safe to delete

---

## To Resume

In new session, say:
> "Read `.agent/plans/SESSION_HANDOFF.md` and continue with Sub-Plan 2.5: Realtime Ingestion Status"
