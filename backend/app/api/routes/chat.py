import base64
import json
import logging
import re
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
    """Send a message and stream the assistant's response with RAG."""
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

    # Retrieve relevant context from user's documents
    retrieval = RetrievalService(embedding_service, supabase)
    try:
        chunks = await retrieval.retrieve(
            query=message.content,
            user_id=user.sub,
            metadata_filter=message.metadata_filter,
        )
    except Exception as e:
        logger.warning("Retrieval failed, proceeding without context: %s", e)
        chunks = []

    # Build system prompt with or without RAG context
    image_refs = []
    if chunks:
        context_str = format_context(chunks)

        # Collect all document image references from retrieved chunks
        all_image_refs = []
        seen_docs = set()
        for chunk in chunks:
            doc_id = chunk.get("document_id")
            if not doc_id or doc_id in seen_docs:
                continue
            seen_docs.add(doc_id)
            doc = await supabase.get_document(doc_id, user.sub)
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

        # Use LLM to filter images to only those relevant to the user's question
        if all_image_refs:
            image_list = "\n".join(
                f"{i}: {ref['alt']}" + (f" (page {ref['page']})" if ref.get("page") is not None else "")
                for i, ref in enumerate(all_image_refs)
            )
            try:
                filter_response = llm.chat_completion(
                    messages=[{"role": "user", "content": message.content}],
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
                    image_refs = [all_image_refs[i] for i in selected if i < len(all_image_refs)]
                # If "none" or parsing fails, image_refs stays empty
            except Exception:
                logger.warning("Image filtering failed, including all images")
                image_refs = all_image_refs

        if image_refs:
            image_descriptions = []
            for ref in image_refs:
                desc = f"- {ref['alt']}"
                if ref.get("page") is not None:
                    desc += f" (page {ref['page']})"
                image_descriptions.append(desc)
            context_str += "\n\n## Document Images Available\n\n"
            context_str += "The following images were extracted from the retrieved documents and will be shown to the user automatically:\n"
            context_str += "\n".join(image_descriptions)
            context_str += "\n\nYou may reference these images in your answer (e.g. 'as shown in the image from page 3') but do NOT try to reproduce image URLs or markdown image syntax."

        system_prompt = RAG_CONTEXT_TEMPLATE.format(
            base_prompt=BASE_SYSTEM_PROMPT,
            context=context_str,
        )
    else:
        system_prompt = BASE_SYSTEM_PROMPT

    # Get all messages for this thread to build conversation history
    db_messages = await supabase.get_messages(thread_id)

    # Convert to LLM format — handle multimodal messages with image attachments
    chat_messages = []
    for msg in db_messages:
        attachments = msg.get("attachments") or []
        image_attachments = [a for a in attachments if a.get("type") == "image"]

        if image_attachments and msg["role"] == "user":
            # Build multimodal content array
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

            # Send document image references to frontend
            if image_refs:
                yield {"data": json.dumps({"images": image_refs})}

            async for chunk in llm.chat_completion_stream(
                messages=chat_messages,
                system_prompt=system_prompt,
            ):
                full_response += chunk
                yield {"data": json.dumps({"content": chunk})}

            # Build attachments for assistant message (document images)
            assistant_attachments = None
            if image_refs:
                assistant_attachments = [
                    {
                        "type": "document_image",
                        "url": ref["url"],
                        "alt": ref["alt"],
                    }
                    for ref in image_refs
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
            yield {"data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
