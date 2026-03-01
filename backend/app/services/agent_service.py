"""
Agent service: orchestrates the tool-calling loop.

Flow:
1. Call LLM with tools (non-streaming)
2. If tool_calls → execute each, yield events, append results, loop
3. If no tool_calls → final answer, re-run as streaming, yield text chunks
4. Max 5 rounds safety limit
"""

import json
import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator

from app.config import get_settings
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService, format_context
from app.services.sql_service import SQLService
from app.services.web_search_service import WebSearchService
from app.services.supabase_service import SupabaseService
from app.tools.definitions import get_enabled_tools

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5


@dataclass
class ToolCallEvent:
    """Emitted when the LLM decides to call a tool."""
    name: str
    arguments: dict


@dataclass
class ToolResultEvent:
    """Emitted after a tool has been executed."""
    name: str
    result: str


@dataclass
class SourcesEvent:
    """Emitted when retrieval returns document sources."""
    sources: list[dict]


@dataclass
class ImagesEvent:
    """Emitted when retrieval returns document images."""
    images: list[dict]


@dataclass
class SubAgentEvent:
    """Wraps an inner event from a sub-agent for the parent stream."""
    inner: "ToolCallEvent | ToolResultEvent | str"


@dataclass
class AgentContext:
    """Everything the agent loop needs to operate."""
    user_id: str
    query: str
    chat_messages: list[dict]
    system_prompt: str
    llm: LLMService
    embedding_service: EmbeddingService
    supabase: SupabaseService
    metadata_filter: dict | None = None
    # Accumulated across rounds
    sources: list[dict] = field(default_factory=list)
    image_refs: list[dict] = field(default_factory=list)


async def _rewrite_query(llm: LLMService, query: str, chat_messages: list[dict]) -> list[str]:
    """Use the LLM to rewrite a conversational query into 1-3 focused search queries."""
    # Build a compact conversation context (last few messages)
    recent = chat_messages[-6:] if len(chat_messages) > 6 else chat_messages
    conversation = "\n".join(
        f"{m['role'].upper()}: {m['content'] if isinstance(m['content'], str) else m['content'][0].get('text', '')}"
        for m in recent
    )

    try:
        response = llm.chat_completion(
            messages=[{"role": "user", "content": conversation}],
            system_prompt=(
                "Given the conversation above, rewrite the user's latest message into 1-3 focused search queries "
                "for a vector similarity search over document chunks. Resolve pronouns and references using "
                "conversation context. Extract specific keywords and noun phrases. "
                "Return ONLY the queries, one per line. No numbering, no explanation."
            ),
            max_tokens=150,
        )
        queries = [q.strip() for q in response.strip().split("\n") if q.strip()]
        return queries[:3] if queries else [query]
    except Exception:
        logger.warning("Query rewriting failed, using original query")
        return [query]


async def _execute_retrieve(ctx: AgentContext, arguments: dict) -> str:
    """Execute the retrieve_documents tool."""
    query = arguments.get("query", ctx.query)
    retrieval = RetrievalService(ctx.embedding_service, ctx.supabase)
    settings = get_settings()

    # Query rewriting: generate multiple focused queries
    if settings.query_rewrite_enabled:
        queries = await _rewrite_query(ctx.llm, query, ctx.chat_messages)
        logger.info("Rewritten queries: %s", queries)
    else:
        queries = [query]

    # Run retrieval for each query and merge results
    all_chunks: dict[str, dict] = {}  # chunk_id -> chunk (keep highest similarity)
    for q in queries:
        try:
            chunks = await retrieval.retrieve(
                query=q,
                user_id=ctx.user_id,
                metadata_filter=ctx.metadata_filter,
            )
            for chunk in chunks:
                chunk_id = chunk["id"]
                if chunk_id not in all_chunks or chunk.get("similarity", 0) > all_chunks[chunk_id].get("similarity", 0):
                    all_chunks[chunk_id] = chunk
        except Exception as e:
            logger.warning("Retrieval failed for query '%s': %s", q, e)

    # Sort by similarity descending and apply limit
    chunks = sorted(all_chunks.values(), key=lambda c: c.get("similarity", 0), reverse=True)
    chunks = chunks[:settings.retrieval_limit]

    if not chunks:
        return "No relevant documents found."

    # Collect sources for the frontend
    ctx.sources = [
        {"filename": c.get("filename", "Unknown"), "similarity": c.get("similarity", 0)}
        for c in chunks
    ]

    # Collect images from image_description chunks (matched by semantic search)
    # Only include images whose similarity is competitive with the best result
    top_similarity = chunks[0].get("similarity", 0) if chunks else 0
    min_image_similarity = top_similarity * settings.image_similarity_min_ratio
    seen_images = set()
    figure_num = 0
    for chunk in chunks:
        chunk_meta = chunk.get("metadata") or {}
        if chunk_meta.get("chunk_type") == "image_description":
            similarity = chunk.get("similarity", 0)
            if similarity < min_image_similarity:
                continue
            doc_id = chunk.get("document_id")
            img_idx = chunk_meta.get("image_index")
            if doc_id and img_idx is not None and (doc_id, img_idx) not in seen_images:
                seen_images.add((doc_id, img_idx))
                figure_num += 1
                fname = chunk.get("filename", "document")
                page = chunk_meta.get("image_page")
                # Extract short description from chunk content (skip the header line)
                content = chunk.get("content", "")
                desc_lines = content.split("\n", 1)
                description = desc_lines[1].strip()[:120] if len(desc_lines) > 1 else ""
                label = f"Figure {figure_num}"
                page_info = f" (page {page})" if page else ""
                ctx.image_refs.append({
                    "url": f"/api/documents/{doc_id}/images/{img_idx}",
                    "alt": f"{label}: {description}" if description else label,
                    "label": label,
                    "doc_id": doc_id,
                    "index": img_idx,
                    "page": page,
                    "source": fname,
                })
                if len(ctx.image_refs) >= settings.image_max_results:
                    break

    # Log image filtering stats
    total_image_chunks = sum(1 for c in chunks if (c.get("metadata") or {}).get("chunk_type") == "image_description")
    if total_image_chunks:
        logger.info(
            "Image chunks: %d found, %d passed filters (min_ratio=%.2f, min_sim=%.4f, max=%d)",
            total_image_chunks, len(ctx.image_refs),
            settings.image_similarity_min_ratio, min_image_similarity,
            settings.image_max_results,
        )

    context_str = format_context(chunks)

    if ctx.image_refs:
        context_str += "\n\n## Attached Figures\n\n"
        for ref in ctx.image_refs:
            context_str += f"- **{ref['label']}** — {ref['source']}, p.{ref.get('page', '?')}: {ref['alt']}\n"
        context_str += "\nThese figures are displayed below your answer. Reference relevant ones by label (e.g. 'see **Figure 1**'). Do NOT describe figures the user can already see — just refer to them. Do NOT include image URLs."

    return context_str


async def _execute_text_to_sql(ctx: AgentContext, arguments: dict) -> str:
    """Execute the text_to_sql tool."""
    question = arguments.get("question", "")
    sql_service = SQLService(ctx.llm)
    return await sql_service.execute(question, ctx.user_id)


async def _execute_web_search(arguments: dict) -> str:
    """Execute the web_search tool."""
    query = arguments.get("query", "")
    service = WebSearchService()
    return await service.search(query)


MAX_DOCUMENT_CHARS = 80_000

SUB_AGENT_SYSTEM_PROMPT = """You are a document analysis assistant. You have the full text of a document in your context. Answer the user's question about this document thoroughly and accurately.

You have access to the retrieve_documents tool to search within this document for specific sections if needed.

## Document Text

{document_text}"""


async def _execute_analyze_document(
    ctx: AgentContext, arguments: dict
) -> AsyncGenerator[SubAgentEvent | str, None]:
    """
    Execute the analyze_document tool as an async generator.

    Yields SubAgentEvent wrappers for streaming, then yields the final
    answer string as the tool result.
    """
    filename = arguments.get("filename", "")
    question = arguments.get("question", "")

    # Look up document
    doc = await ctx.supabase.get_document_by_filename(ctx.user_id, filename)
    if not doc:
        yield f"Document '{filename}' not found or not yet processed."
        return

    # Load all chunks and assemble full text
    chunks = await ctx.supabase.get_chunks_by_document(doc["id"])
    if not chunks:
        yield f"No content found for document '{filename}'."
        return

    full_text = "\n\n".join(c["content"] for c in chunks)
    if len(full_text) > MAX_DOCUMENT_CHARS:
        full_text = full_text[:MAX_DOCUMENT_CHARS] + "\n\n[... truncated ...]"

    # Build sub-agent context
    sub_system_prompt = SUB_AGENT_SYSTEM_PROMPT.format(document_text=full_text)
    sub_ctx = AgentContext(
        user_id=ctx.user_id,
        query=question,
        chat_messages=[{"role": "user", "content": question}],
        system_prompt=sub_system_prompt,
        llm=ctx.llm,
        embedding_service=ctx.embedding_service,
        supabase=ctx.supabase,
        metadata_filter=None,
    )

    # Run sub-agent loop, wrapping each event
    final_answer = ""
    async for event in run_agent_loop(sub_ctx):
        if isinstance(event, (ToolCallEvent, ToolResultEvent)):
            yield SubAgentEvent(inner=event)
        elif isinstance(event, str):
            final_answer += event
            yield SubAgentEvent(inner=event)
        # SourcesEvent / ImagesEvent from sub-agent are silently dropped

    # Yield the final answer as a plain string (becomes the tool result)
    yield final_answer


TOOL_EXECUTORS = {
    "retrieve_documents": _execute_retrieve,
    "text_to_sql": _execute_text_to_sql,
    "web_search": _execute_web_search,
}


async def run_agent_loop(
    ctx: AgentContext,
) -> AsyncGenerator[ToolCallEvent | ToolResultEvent | SourcesEvent | ImagesEvent | SubAgentEvent | str, None]:
    """
    Run the agentic tool-calling loop.

    Yields:
      - ToolCallEvent when the LLM calls a tool
      - ToolResultEvent after execution
      - SourcesEvent / ImagesEvent for document retrieval metadata
      - str chunks for the final streamed answer
    """
    settings = get_settings()
    tools = get_enabled_tools(settings)

    # Build the message list for the LLM (system prompt is passed separately)
    messages = list(ctx.chat_messages)

    for _round in range(MAX_ROUNDS):
        # Non-streaming call to see if the LLM wants to use tools
        response_msg = ctx.llm.chat_completion_with_tools(
            messages=messages,
            system_prompt=ctx.system_prompt,
            tools=tools,
        )

        if not response_msg.tool_calls:
            # No tool calls — this is the final answer. Stream it.
            # Re-run as streaming with the accumulated messages
            # First append the assistant's decision (no tool calls) content if any
            # We stream fresh instead of using the non-streaming content
            async for chunk in ctx.llm.chat_completion_stream(
                messages=messages,
                system_prompt=ctx.system_prompt,
            ):
                yield chunk
            return

        # The LLM wants to call tools
        # Append the assistant message with tool_calls to history
        messages.append(response_msg.to_dict())

        for tool_call in response_msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            yield ToolCallEvent(name=fn_name, arguments=fn_args)

            # Execute the tool
            if fn_name == "analyze_document":
                # analyze_document is an async generator yielding SubAgentEvents
                result = ""
                try:
                    async for sub_event in _execute_analyze_document(ctx, fn_args):
                        if isinstance(sub_event, SubAgentEvent):
                            yield sub_event
                        elif isinstance(sub_event, str):
                            # Final answer string from the sub-agent
                            result = sub_event
                except Exception as e:
                    logger.error("Tool %s failed: %s", fn_name, e)
                    result = f"Tool execution failed: {e}"
            else:
                executor = TOOL_EXECUTORS.get(fn_name)
                if executor is None:
                    result = f"Unknown tool: {fn_name}"
                else:
                    try:
                        if fn_name == "web_search":
                            result = await executor(fn_args)
                        else:
                            result = await executor(ctx, fn_args)
                    except Exception as e:
                        logger.error("Tool %s failed: %s", fn_name, e)
                        result = f"Tool execution failed: {e}"

            yield ToolResultEvent(name=fn_name, result=result)

            # Emit sources/images after retrieval
            if fn_name == "retrieve_documents":
                if ctx.sources:
                    yield SourcesEvent(sources=ctx.sources)
                if ctx.image_refs:
                    yield ImagesEvent(images=ctx.image_refs)

            # Append tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # Safety: if we've exhausted rounds, stream whatever we have
    async for chunk in ctx.llm.chat_completion_stream(
        messages=messages,
        system_prompt=ctx.system_prompt,
    ):
        yield chunk
