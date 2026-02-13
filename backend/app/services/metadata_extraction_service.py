import json
import logging

from app.models.metadata import ExtractedMetadata
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are a metadata extraction assistant. Analyze the provided document text and extract structured metadata.

Return ONLY valid JSON with exactly these fields:
{
  "title": "document title (infer from content if not explicit)",
  "summary": "2-3 sentence summary of the document",
  "topics": ["topic1", "topic2", ...],
  "document_type": "one of: report, article, email, code, notes, manual, specification, other",
  "language": "ISO 639-1 language code (e.g. en, es, fr)",
  "key_entities": ["entity1", "entity2", ...]
}

Rules:
- topics: 3-7 key topics
- key_entities: up to 10 notable people, organizations, products, or locations
- document_type: choose the single best fit from the allowed values
- Return ONLY the JSON object, no markdown fences, no explanation"""


def _truncate_text(text: str, max_chars: int = 8000) -> str:
    """Truncate to first 4000 + last 4000 chars if text exceeds max_chars."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[... middle truncated ...]\n\n" + text[-half:]


def extract_metadata(text: str, filename: str) -> ExtractedMetadata:
    """Extract structured metadata from document text using LLM."""
    try:
        llm = get_llm_service()
        truncated = _truncate_text(text)

        response = llm.chat_completion(
            messages=[{"role": "user", "content": truncated}],
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            max_tokens=1000,
        )

        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag)
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        metadata = ExtractedMetadata(**data)
        logger.info("Extracted metadata for '%s': type=%s, %d topics", filename, metadata.document_type, len(metadata.topics))
        return metadata

    except Exception as e:
        logger.warning("Metadata extraction failed for '%s': %s — using fallback", filename, e)
        return ExtractedMetadata(
            title=filename,
            summary="Metadata extraction failed.",
            topics=[],
            document_type="other",
            language="en",
            key_entities=[],
        )
