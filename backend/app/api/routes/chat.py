import base64
import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from app.api.middleware.auth import get_current_user, TokenPayload
from app.models.chat import (
    ThreadResponse,
    ThreadWithMessages,
    MessageCreate,
    MessageResponse,
)
from app.services.supabase_service import SupabaseService, get_supabase_service
from app.services.storage_service import StorageService, get_storage_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.agent_service import (
    AgentContext,
    run_agent_loop,
    ToolCallEvent,
    ToolResultEvent,
    SourcesEvent,
    ImagesEvent,
    SubAgentEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter()

SYSTEM_PROMPT = """You are a precise document assistant. You answer strictly from the user's uploaded documents. Never pad answers with general knowledge or filler.

## Rules
1. ALWAYS call `retrieve_documents` FIRST for any document-related question. Never answer from your own knowledge.
2. Answer ONLY what was asked. Do not add background context, definitions, or tangential information unless requested.
3. Structure every answer clearly:
   - Use **bold** for key terms and headings
   - Use bullet points or numbered lists for multiple items
   - Keep paragraphs short (2-3 sentences max)
4. Cite sources inline: (Source: filename.pdf, page X)
5. If retrieval returns nothing relevant, say so directly — do not guess.

## Tools
- **retrieve_documents**: Search document content. Use for ANY factual question.
- **text_to_sql**: Query document metadata (counts, types, topics, dates).
- **web_search**: Search the web for current information (when configured).
- **analyze_document**: Deep analysis of a whole document (summaries, themes). Not for simple lookups.

## Document Images
- Diagrams, charts, and figures from documents are indexed and searchable via `retrieve_documents`.
- When images match, they are shown to the user automatically below your answer with figure labels.
- Reference them by label (e.g. "see **Figure 1**") — do NOT recreate, describe, or reproduce image URLs.
- Only mention figures that are directly relevant to the question.

## Mermaid Diagrams
- Only generate Mermaid when the user explicitly asks to CREATE or DRAW a new diagram.
- Also use Mermaid to render mermaid code blocks found in markdown documents.
- Wrap in ```mermaid code blocks."""


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


@router.post("/threads/{thread_id}/images")
async def upload_chat_image(
    thread_id: str,
    file: UploadFile = File(...),
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
    storage: StorageService = Depends(get_storage_service),
):
    """Upload an image for use in a chat message."""
    thread = await supabase.get_thread(thread_id, user.sub)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large (max 10MB)")

    ext = content_type.split("/")[-1].split("+")[0]
    image_name = f"{uuid.uuid4().hex[:8]}.{ext}"

    storage_path = await storage.upload_chat_image(
        user_id=user.sub,
        thread_id=thread_id,
        image_name=image_name,
        content=content,
        content_type=content_type,
    )

    url = f"/api/threads/{thread_id}/images/{image_name}"
    return {"storage_path": storage_path, "url": url}


@router.get("/threads/{thread_id}/images/{image_name}")
async def get_chat_image(
    thread_id: str,
    image_name: str,
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
    storage: StorageService = Depends(get_storage_service),
):
    """Serve a chat image."""
    thread = await supabase.get_thread(thread_id, user.sub)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    storage_path = f"{user.sub}/{thread_id}/{image_name}"
    try:
        content = await storage.download_chat_image(storage_path)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    ext = image_name.rsplit(".", 1)[-1] if "." in image_name else "png"
    media_type = f"image/{ext}"
    return Response(content=content, media_type=media_type)


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    message: MessageCreate,
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
    storage: StorageService = Depends(get_storage_service),
    llm: LLMService = Depends(get_llm_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Send a message and stream the assistant's response via agent loop."""
    # Verify thread ownership
    thread = await supabase.get_thread(thread_id, user.sub)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    # Save user message to database (with attachments if any)
    attachments_data = None
    if message.attachments:
        attachments_data = [a.model_dump() for a in message.attachments]
    await supabase.create_message(
        thread_id=thread_id,
        role="user",
        content=message.content,
        attachments=attachments_data,
    )

    # Generate title if this is the first message
    if not thread.get("title"):
        try:
            title = llm.generate_title(message.content)
            await supabase.update_thread(thread_id, user.sub, title)
        except Exception:
            pass  # Title generation is not critical

    # Get all messages for this thread to build conversation history
    db_messages = await supabase.get_messages(thread_id)

    # Convert to LLM format — handle multimodal messages with image attachments
    chat_messages = []
    for msg in db_messages:
        attachments = msg.get("attachments") or []
        image_attachments = [a for a in attachments if a.get("type") == "image"]

        if image_attachments and msg["role"] == "user":
            content_parts = [{"type": "text", "text": msg["content"]}]
            for att in image_attachments:
                try:
                    img_bytes = await storage.download_chat_image(att["storage_path"])
                    b64_data = base64.b64encode(img_bytes).decode("utf-8")
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_data}"},
                    })
                except Exception:
                    logger.warning("Failed to load chat image: %s", att.get("storage_path"))
            chat_messages.append({"role": msg["role"], "content": content_parts})
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})

    # Build agent context
    ctx = AgentContext(
        user_id=user.sub,
        query=message.content,
        chat_messages=chat_messages,
        system_prompt=SYSTEM_PROMPT,
        llm=llm,
        embedding_service=embedding_service,
        supabase=supabase,
        metadata_filter=message.metadata_filter,
    )

    async def event_generator():
        full_response = ""
        try:
            async for event in run_agent_loop(ctx):
                if isinstance(event, SubAgentEvent):
                    inner = event.inner
                    if isinstance(inner, ToolCallEvent):
                        yield {"data": json.dumps({"sub_agent_event": {"type": "tool_call", "tool_call": {"name": inner.name, "arguments": inner.arguments}}})}
                    elif isinstance(inner, ToolResultEvent):
                        display_result = inner.result[:2000] + "..." if len(inner.result) > 2000 else inner.result
                        yield {"data": json.dumps({"sub_agent_event": {"type": "tool_result", "tool_result": {"name": inner.name, "result": display_result}}})}
                    elif isinstance(inner, str):
                        yield {"data": json.dumps({"sub_agent_event": {"type": "content", "content": inner}})}
                elif isinstance(event, ToolCallEvent):
                    yield {"data": json.dumps({"tool_call": {"name": event.name, "arguments": event.arguments}})}
                elif isinstance(event, ToolResultEvent):
                    # Truncate long results for the SSE event (full result stays in LLM context)
                    display_result = event.result[:2000] + "..." if len(event.result) > 2000 else event.result
                    yield {"data": json.dumps({"tool_result": {"name": event.name, "result": display_result}})}
                elif isinstance(event, SourcesEvent):
                    yield {"data": json.dumps({"sources": event.sources})}
                elif isinstance(event, ImagesEvent):
                    yield {"data": json.dumps({"images": event.images})}
                elif isinstance(event, str):
                    full_response += event
                    yield {"data": json.dumps({"content": event})}

            # Build attachments for assistant message (document images)
            assistant_attachments = None
            if ctx.image_refs:
                assistant_attachments = [
                    {
                        "type": "document_image",
                        "url": ref["url"],
                        "alt": ref["alt"],
                        "label": ref.get("label", ""),
                    }
                    for ref in ctx.image_refs
                ]

            # Save assistant message to database
            await supabase.create_message(
                thread_id=thread_id,
                role="assistant",
                content=full_response,
                attachments=assistant_attachments,
            )

            yield {"data": "[DONE]"}
        except Exception as e:
            logger.error("Agent loop error: %s", e)
            yield {"data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
