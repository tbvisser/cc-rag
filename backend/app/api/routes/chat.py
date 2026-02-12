import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.api.middleware.auth import get_current_user, TokenPayload
from app.models.chat import (
    ThreadResponse,
    ThreadWithMessages,
    MessageCreate,
    MessageResponse,
)
from app.services.supabase_service import SupabaseService, get_supabase_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.retrieval_service import RetrievalService, format_context

logger = logging.getLogger(__name__)

router = APIRouter()

# Base system prompt
BASE_SYSTEM_PROMPT = """You are a helpful AI assistant with access to the user's uploaded documents.
Answer questions based on the provided context when available. If the context doesn't contain
relevant information, use your general knowledge and let the user know.
Be concise and helpful. Cite source documents when using retrieved context."""

RAG_CONTEXT_TEMPLATE = """{base_prompt}

## Retrieved Context

The following excerpts were retrieved from the user's documents and may be relevant to their question:

{context}

Use the above context to inform your answer. Cite the source when you use information from it."""


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """Create a new chat thread."""
    thread = await supabase.create_thread(user_id=user.sub)
    return thread


@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """List all threads for the current user."""
    threads = await supabase.get_threads(user.sub)
    return threads


@router.get("/threads/{thread_id}", response_model=ThreadWithMessages)
async def get_thread(
    thread_id: str,
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """Get a thread with its messages."""
    thread = await supabase.get_thread(thread_id, user.sub)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    messages = await supabase.get_messages(thread_id)
    return {**thread, "messages": messages}


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """Delete a thread."""
    thread = await supabase.get_thread(thread_id, user.sub)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    await supabase.delete_thread(thread_id, user.sub)


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    message: MessageCreate,
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
    llm: LLMService = Depends(get_llm_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Send a message and stream the assistant's response with RAG."""
    # Verify thread ownership
    thread = await supabase.get_thread(thread_id, user.sub)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    # Save user message to database
    await supabase.create_message(
        thread_id=thread_id,
        role="user",
        content=message.content,
    )

    # Generate title if this is the first message
    if not thread.get("title"):
        try:
            title = llm.generate_title(message.content)
            await supabase.update_thread(thread_id, user.sub, title)
        except Exception:
            pass  # Title generation is not critical

    # Retrieve relevant context from user's documents
    retrieval = RetrievalService(embedding_service, supabase)
    try:
        chunks = await retrieval.retrieve(
            query=message.content,
            user_id=user.sub,
        )
    except Exception as e:
        logger.warning("Retrieval failed, proceeding without context: %s", e)
        chunks = []

    # Build system prompt with or without RAG context
    if chunks:
        context_str = format_context(chunks)
        system_prompt = RAG_CONTEXT_TEMPLATE.format(
            base_prompt=BASE_SYSTEM_PROMPT,
            context=context_str,
        )
    else:
        system_prompt = BASE_SYSTEM_PROMPT

    # Get all messages for this thread to build conversation history
    db_messages = await supabase.get_messages(thread_id)

    # Convert to LLM format
    chat_messages = [
        {"role": msg["role"], "content": msg["content"]} for msg in db_messages
    ]

    async def event_generator():
        full_response = ""
        try:
            # Send sources metadata to frontend before streaming
            if chunks:
                sources = [
                    {"filename": c.get("filename", "Unknown"), "similarity": c.get("similarity", 0)}
                    for c in chunks
                ]
                yield {"data": json.dumps({"sources": sources})}

            async for chunk in llm.chat_completion_stream(
                messages=chat_messages,
                system_prompt=system_prompt,
            ):
                full_response += chunk
                yield {"data": json.dumps({"content": chunk})}

            # Save assistant message to database
            await supabase.create_message(
                thread_id=thread_id,
                role="assistant",
                content=full_response,
            )

            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
