import io
import json
import logging
import os
import tempfile

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from pydantic import AnyUrl

from app.config import get_settings
from app.services.storage_service import StorageService
from app.services.supabase_service import SupabaseService
from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingService
from app.services.metadata_extraction_service import extract_metadata

logger = logging.getLogger(__name__)


# Map MIME types to docling InputFormat + temp-file suffix
DOCLING_TYPES: dict[str, tuple[InputFormat, str]] = {
    "application/pdf": (InputFormat.PDF, ".pdf"),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        InputFormat.DOCX,
        ".docx",
    ),
    "text/html": (InputFormat.HTML, ".html"),
    "text/markdown": (InputFormat.MD, ".md"),
}


def _build_converter() -> DocumentConverter:
    """Build a singleton DocumentConverter with optimised pipeline options."""
    pdf_options = PdfPipelineOptions(
        do_table_structure=True,
        do_ocr=True,
        generate_picture_images=True,
        images_scale=2.0,
    )

    return DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.DOCX,
            InputFormat.HTML,
            InputFormat.MD,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
        },
    )


# Singleton — models loaded once, reused across requests
_converter: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        logger.info("Initialising docling DocumentConverter (first call — may download models)")
        _converter = _build_converter()
        logger.info("Docling DocumentConverter ready")
    return _converter


def extract_text(content: bytes, file_type: str) -> tuple[str, list[dict]]:
    """Extract plain text (and images if available) from file content based on MIME type."""
    if file_type in DOCLING_TYPES:
        _, suffix = DOCLING_TYPES[file_type]
        return _extract_with_docling(content, suffix)

    if file_type == "application/json":
        data = json.loads(content.decode("utf-8"))
        return json.dumps(data, indent=2), []

    # text/plain, text/csv — just decode
    return content.decode("utf-8"), []


def _extract_with_docling(content: bytes, suffix: str) -> tuple[str, list[dict]]:
    """Extract text and images using the singleton DocumentConverter."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        converter = _get_converter()
        result = converter.convert(tmp_path)
        text = result.document.export_to_markdown()

        # Extract images from Docling result
        images = []
        for i, picture in enumerate(result.document.pictures):
            image_ref = picture.image
            if image_ref is None:
                continue
            # image_ref is a Docling ImageRef; get the actual PIL image
            pil_image = image_ref.pil_image if hasattr(image_ref, 'pil_image') else image_ref
            if pil_image is None:
                continue
            page_no = picture.prov[0].page_no if picture.prov else None
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            images.append({
                "index": i,
                "png_bytes": buf.getvalue(),
                "page": page_no,
            })

        logger.info("Docling extracted %d images", len(images))
        return text, images
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


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

        # Get document record
        doc = await supabase._request(
            "GET", "documents", params={"id": f"eq.{document_id}"}
        )
        if not doc or (isinstance(doc, list) and len(doc) == 0):
            raise ValueError(f"Document {document_id} not found")
        doc = doc[0] if isinstance(doc, list) else doc

        # Download file from storage
        content = await storage.download_file(doc["storage_path"])
        logger.info(
            "Document %s (%s): downloaded %d bytes, type=%s",
            document_id, doc["filename"], len(content), doc["file_type"],
        )

        # Extract text and images
        text, images = extract_text(content, doc["file_type"])
        if not text.strip():
            raise ValueError("No text content could be extracted from the file")
        logger.info("Document %s: extracted %d chars of text, %d images", document_id, len(text), len(images))

        # Upload extracted images to storage
        image_metadata_list = []
        if images:
            await storage.ensure_images_bucket()
            for img in images:
                image_name = f"{img['index']}.png"
                storage_path = await storage.upload_image(
                    user_id=doc["user_id"],
                    document_id=document_id,
                    image_name=image_name,
                    content=img["png_bytes"],
                    content_type="image/png",
                )
                image_metadata_list.append({
                    "storage_path": storage_path,
                    "index": img["index"],
                    "page": img["page"],
                })
            logger.info("Document %s: uploaded %d images to storage", document_id, len(image_metadata_list))

        # Extract metadata using LLM
        metadata = extract_metadata(text, doc["filename"])
        metadata_dict = metadata.model_dump()
        if image_metadata_list:
            metadata_dict["images"] = image_metadata_list
        logger.info("Document %s: metadata = %s", document_id, metadata_dict)

        update_result = await supabase.update_document_metadata(document_id, metadata_dict)
        logger.info("Document %s: metadata saved (rows=%s)", document_id,
                     len(update_result) if isinstance(update_result, list) else update_result)

        # Chunk the text
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Text produced no chunks after splitting")

        logger.info(
            "Document %s: split into %d chunks",
            document_id, len(chunks),
        )

        # Generate embeddings
        embeddings = await embedding_service.embed_chunks(chunks)

        # Store chunks with embeddings in database
        chunk_metadata = {
            "document_type": metadata.document_type,
            "topics": metadata.topics,
            "language": metadata.language,
        }
        chunk_records = [
            {
                "document_id": document_id,
                "content": chunk_content,
                "chunk_index": i,
                "embedding": embedding,
                "metadata": chunk_metadata,
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
        logger.error("Document %s: ingestion failed - %s", document_id, str(e), exc_info=True)
        await supabase.update_document_status(
            document_id, "failed", error_message=str(e)
        )
