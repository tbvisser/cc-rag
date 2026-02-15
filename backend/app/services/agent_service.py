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
import re
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


async def _execute_retrieve(ctx: AgentContext, arguments: dict) -> str:
    """Execute the retrieve_documents tool."""
    query = arguments.get("query", ctx.query)
    retrieval = RetrievalService(ctx.embedding_service, ctx.supabase)

    try:
        chunks = await retrieval.retrieve(
            query=query,
            user_id=ctx.user_id,
            metadata_filter=ctx.metadata_filter,
        )
    except Exception as e:
        logger.warning("Retrieval failed: %s", e)
        return "Retrieval failed — no documents found."

    if not chunks:
        return "No relevant documents found."

    # Collect sources for the frontend
    ctx.sources = [
        {"filename": c.get("filename", "Unknown"), "similarity": c.get("similarity", 0)}
        for c in chunks
    ]

    # Collect document images
    all_image_refs = []
    seen_docs = set()
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        if not doc_id or doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        doc = await ctx.supabase.get_document(doc_id, ctx.user_id)
        if doc and doc.get("metadata", {}).get("images"):
            for img in doc["metadata"]["images"]:
                fname = chunk.get("filename", "document")
                all_image_refs.append({
                    "url": f"/api/documents/{doc_id}/images/{img['index']}",
                    "alt": f"Image {img['index']} from {fname}",
                    "doc_id": doc_id,
                    "index": img["index"],
                    "page": img.get("page"),
                })

    # Filter images using LLM
    if all_image_refs:
        image_list = "\n".join(
            f"{i}: {ref['alt']}" + (f" (page {ref['page']})" if ref.get("page") is not None else "")
            for i, ref in enumerate(all_image_refs)
        )
        try:
            filter_response = ctx.llm.chat_completion(
                messages=[{"role": "user", "content": ctx.query}],
                system_prompt=(
                    "The user asked a question about a document. Below is a numbered list of images "
                    "extracted from that document. Return ONLY the comma-separated numbers of images "
                    "that are relevant to the user's question. If none are relevant, return \"none\".\n\n"
                    f"Images:\n{image_list}"
                ),
                max_tokens=50,
            )
            filter_text = filter_response.strip().lower()
            if filter_text != "none":
                selected = [int(x) for x in re.findall(r"\d+", filter_text)]
                ctx.image_refs = [all_image_refs[i] for i in selected if i < len(all_image_refs)]
        except Exception:
            logger.warning("Image filtering failed, including all images")
            ctx.image_refs = all_image_refs

    context_str = format_context(chunks)

    if ctx.image_refs:
        image_descriptions = []
        for ref in ctx.image_refs:
            desc = f"- {ref['alt']}"
            if ref.get("page") is not None:
                desc += f" (page {ref['page']})"
            image_descriptions.append(desc)
        context_str += "\n\n## Document Images Available\n\n"
        context_str += "The following images were extracted from the retrieved documents and will be shown to the user automatically:\n"
        context_str += "\n".join(image_descriptions)
        context_str += "\n\nYou may reference these images in your answer but do NOT try to reproduce image URLs."

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
