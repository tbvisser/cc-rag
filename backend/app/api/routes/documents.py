import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status

from app.api.middleware.auth import get_current_user, TokenPayload
from app.models.document import DocumentResponse
from app.services.supabase_service import SupabaseService, get_supabase_service
from app.services.storage_service import StorageService, get_storage_service
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.ingestion_service import process_document

router = APIRouter()

ALLOWED_TYPES = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/pdf": ".pdf",
    "application/json": ".json",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
    storage: StorageService = Depends(get_storage_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Upload a document for RAG processing."""
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{content_type}' not supported. Allowed: {', '.join(ALLOWED_TYPES.keys())}",
        )

    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )

    # Generate unique filename to avoid collisions
    original_name = file.filename or "untitled"
    unique_name = f"{uuid.uuid4().hex[:8]}_{original_name}"

    # Upload to Supabase Storage
    await storage.ensure_bucket()
    storage_path = await storage.upload_file(
        user_id=user.sub,
        filename=unique_name,
        content=content,
        content_type=content_type,
    )

    # Create document record in database
    document = await supabase.create_document(
        user_id=user.sub,
        filename=original_name,
        file_type=content_type,
        file_size=file_size,
        storage_path=storage_path,
    )

    # Trigger background ingestion: chunk → embed → store
    background_tasks.add_task(
        process_document,
        document_id=document["id"],
        storage=storage,
        supabase=supabase,
        embedding_service=embedding_service,
    )

    return document


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """List all documents for the current user."""
    documents = await supabase.get_documents(user.sub)
    return documents


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """Get a specific document."""
    document = await supabase.get_document(document_id, user.sub)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: TokenPayload = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
    storage: StorageService = Depends(get_storage_service),
):
    """Delete a document, its chunks, and its storage file."""
    document = await supabase.get_document(document_id, user.sub)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete chunks first (foreign key constraint)
    await supabase.delete_chunks_by_document(document_id)

    # Delete file from storage
    await storage.delete_file(document["storage_path"])

    # Delete document record
    await supabase.delete_document(document_id, user.sub)
