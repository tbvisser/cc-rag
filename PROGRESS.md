# Progress

Track your progress through the masterclass. Update this file as you complete modules - Claude Code reads this to understand where you are in the project.

## Convention
- `[ ]` = Not started
- `[-]` = In progress
- `[x]` = Completed

## Modules

### Module 1: App Shell + Observability
- [x] Sub-Plan 1.1: Project Scaffolding + Environment
- [x] Sub-Plan 1.2: Supabase Setup + Authentication
- [x] Sub-Plan 1.3: Chat UI + State Management
- [x] Sub-Plan 1.4: OpenAI + LangSmith + SSE Streaming

**Status:** ✅ Complete and validated

**Validated:**
- Sign up / login works
- Create and switch between threads
- Messages stream in real-time
- Messages persist across refresh
- RLS enforced (users only see own threads)

**Notes:**
- Supabase Python SDK removed due to Python 3.14 build issues. Using httpx REST calls instead.
- LangSmith SDK deferred. Can be added later.
- Auth middleware updated to support ES256 JWT (Supabase JWKS).

### Module 2: BYO Retrieval + Memory
- [x] Sub-Plan 2.1: Schema Refactor + Chat Completions Migration
- [x] Sub-Plan 2.2: Document Storage + Upload UI
- [x] Sub-Plan 2.3: Chunking + Embedding Pipeline
- [x] Sub-Plan 2.4: Retrieval Tool + RAG Integration
- [x] Sub-Plan 2.5: Realtime Ingestion Status

**Status:** ✅ Complete. Full RAG pipeline with realtime status updates.

**Validated:**
- Document upload triggers background ingestion
- Status updates (pending → processing → completed/failed) arrive via Supabase Realtime
- No page refresh needed — StatusBadge updates live via websocket
- RLS ensures users only receive updates for their own documents
