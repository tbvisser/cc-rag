import io
import json
import logging

from pypdf import PdfReader

from app.services.storage_service import StorageService
from app.services.supabase_service import SupabaseService
from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def extract_text(content: bytes, file_type: str) -> str:
    """Extract plain text from file content based on MIME type."""
    if file_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)

    if file_type == "application/json":
        data = json.loads(content.decode("utf-8"))
        return json.dumps(data, indent=2)

    # text/plain, text/markdown, text/csv - just decode
    return content.decode("utf-8")


async def process_document(
    document_id: str,
    storage: StorageService,
    supabase: SupabaseService,
    embedding_service: EmbeddingService,
) -> None:
    """
    Full ingestion pipeline: download → extract text → chunk → embed → store.

    Updates document status throughout the process.
    """
    try:
        # Mark as processing
        await supabase.update_document_status(document_id, "processing")

        # Get document metadata
        doc = await supabase._request(
            "GET", "documents", params={"id": f"eq.{document_id}"}
        )
        if not doc or (isinstance(doc, list) and len(doc) == 0):
            raise ValueError(f"Document {document_id} not found")
        doc = doc[0] if isinstance(doc, list) else doc

        # Download file from storage
        content = await storage.download_file(doc["storage_path"])

        # Extract text
        text = extract_text(content, doc["file_type"])
        if not text.strip():
            raise ValueError("No text content could be extracted from the file")

        # Chunk the text
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Text produced no chunks after splitting")

        logger.info(
            "Document %s: extracted %d chars, split into %d chunks",
            document_id,
            len(text),
            len(chunks),
        )

        # Generate embeddings
        embeddings = await embedding_service.embed_chunks(chunks)

        # Store chunks with embeddings in database
        chunk_records = [
            {
                "document_id": document_id,
                "content": chunk_content,
                "chunk_index": i,
                "embedding": embedding,
                "metadata": {},
            }
            for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings))
        ]
        await supabase.create_chunks(chunk_records)

        # Mark as completed
        await supabase.update_document_status(
            document_id, "completed", chunk_count=len(chunks)
        )

        logger.info("Document %s: ingestion complete (%d chunks)", document_id, len(chunks))

    except Exception as e:
        logger.error("Document %s: ingestion failed - %s", document_id, str(e))
        await supabase.update_document_status(
            document_id, "failed", error_message=str(e)
        )
