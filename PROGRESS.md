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

### Module 3: Record Manager
- [x] Content hashing (SHA-256)
- [x] Duplicate detection on upload (returns existing doc with X-Duplicate header)
- [x] DB schema: content_hash column + partial unique index
- [x] Frontend duplicate feedback

**Status:** ✅ Complete.

**Validated:**
- Re-uploading identical file returns existing record without re-processing
- User sees "This document has already been uploaded" message

### Module 4: Metadata Extraction
- [x] ExtractedMetadata Pydantic model (title, summary, topics, type, language, entities)
- [x] LLM-based metadata extraction service with fallback
- [x] DB schema: metadata JSONB column + GIN indexes
- [x] Metadata saved during ingestion (document-level + chunk-level)
- [x] Metadata-enhanced retrieval (filter_metadata in vector search)
- [x] Frontend metadata display (summary, type badge, topic pills)

**Status:** ✅ Complete.

**Validated:**
- PDF upload extracts rich metadata via LLM (title, summary, topics, entities)
- Metadata persisted to documents table JSONB column
- Frontend shows summary, document_type badge, and topic pills on completed docs
- Retrieval supports metadata filtering via `@>` containment

### Module 5: Multi-Format Support
- [x] Docling integration with singleton DocumentConverter
- [x] PDF/DOCX/HTML/Markdown support via docling (OCR + table structure + layout)
- [x] Backend route + storage bucket MIME config updated
- [x] Frontend upload UI accepts all formats
- [x] Cascade deletes (chunks auto-removed via ON DELETE CASCADE)
- [x] Supabase service fixes (updated_at trigger, delete_file error handling)

**Status:** ✅ Complete.

**Validated:**
- PDF upload: 212KB doc extracted 12,483 chars in 9s, 21 chunks, full metadata
- PDF upload: 3.5MB doc extracted 77,860 chars in 124s (OCR + layout), 129 chunks, full metadata
- Both documents show metadata in frontend (title, summary, type, topics)
- Cascade delete confirmed: removing document auto-deletes chunks

**Notes:**
- First docling call downloads OCR models (~40MB) — one-time cost
- Large PDFs (40+ pages) take ~2 min on CPU — expected for OCR + layout detection
- Always kill stale server processes before restart (multiple uvicorn instances cause ghost requests)

### Module 6: Hybrid Search & Reranking
- [x] SQL migration: tsvector GENERATED column + GIN index + `search_chunks_keyword()` RPC
- [x] Config: search_mode, hybrid_alpha, rrf_k, hybrid_candidate_limit, rerank settings
- [x] Supabase service: `search_chunks_keyword()` method
- [x] Reranking service: Cohere cross-encoder via raw httpx (graceful fallback)
- [x] Retrieval service: hybrid search + RRF fusion + optional reranking
- [x] Settings API + UI: retrieval config section (search mode, alpha slider, reranking toggle)

**Status:** ✅ Complete.

**Notes:**
- Three search modes: `vector` (original), `keyword` (FTS), `hybrid` (RRF fusion)
- RRF formula: `score = alpha * 1/(k+vector_rank) + (1-alpha) * 1/(k+keyword_rank)`
- Reranking uses Cohere Rerank v2 API via raw httpx (no SDK dependency)
- `fts` column is `GENERATED ALWAYS AS ... STORED` — auto-backfills existing rows, no ingestion changes needed
- Run `005_hybrid_search.sql` migration in Supabase SQL editor before testing

### Module 7: Additional Tools
- [x] Agentic tool-calling loop (LLM decides which tools to use)
- [x] Tool definitions (retrieve_documents, text_to_sql, web_search)
- [x] Agent service orchestrator with max 5 rounds
- [x] Text-to-SQL tool (LLM generates SELECT, executes via Supabase RPC)
- [x] Web search tool (Tavily API via raw httpx)
- [x] Chat endpoint refactored from hard-coded retrieval to agent loop
- [x] Frontend: SSE tool_call/tool_result events, ToolCallCard UI
- [x] Settings: Tavily API key configuration

**Status:** ✅ Complete.

**Validated:**
- Document retrieval tool: ask about uploaded docs → `retrieve_documents` tool called, sources appear, response cites them
- Text-to-SQL: ask "how many documents have I uploaded?" → `text_to_sql` tool called, SQL generated and executed
- Web search: Tavily key configured, ask about current events → `web_search` tool called, web sources returned
- No tools needed: simple questions get direct responses without tool calls
- ToolCallCard UI: collapsible cards show tool name, arguments, and results during streaming

**Notes:**
- LLM autonomously chooses tools via OpenAI function-calling format
- Agent loop: non-streaming tool calls → execute → feed back → stream final answer
- Text-to-SQL uses `execute_readonly_sql` Supabase RPC (SECURITY DEFINER, SELECT-only)
- Web search only enabled when Tavily API key is configured
- Run `007_text_to_sql.sql` migration in Supabase SQL editor before testing

### Module 8: Sub-Agents
- [x] `analyze_document` tool definition (filename + question params)
- [x] DB helpers: `get_document_by_filename`, `get_chunks_by_document`
- [x] `SubAgentEvent` wrapper + `_execute_analyze_document` async generator
- [x] Sub-agent reuses `run_agent_loop` with full document in system prompt
- [x] SSE serialization for `sub_agent_event` (tool_call, tool_result, content)
- [x] Frontend: `onSubAgentEvent` callback in useSSE + useChat state extension
- [x] Nested sub-agent UI in ToolCallCard (recursive rendering, markdown content)

**Status:** ✅ Complete.

**Notes:**
- Sub-agent spawned via recursive `run_agent_loop` call with document-scoped context
- Full document text assembled from chunks and placed in sub-agent system prompt (80K char limit)
- Sub-agent's `retrieve_documents` calls are scoped to the target document via `metadata_filter`
- `SubAgentEvent` wrapper cleanly separates sub-agent events from main agent events at SSE layer
- ToolCallCard renders sub-agent activity (nested tool calls + streaming markdown) inline
