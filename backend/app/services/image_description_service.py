"""Generate text descriptions of document images using a vision LLM."""

import base64
import logging

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

DESCRIBE_PROMPT = (
    "Describe this image from a document. Include:\n"
    "1. Type of visual (diagram, chart, photo, table, screenshot, etc.)\n"
    "2. All visible text and labels\n"
    "3. Structure, relationships, or flow shown\n"
    "4. Key data points or quantities\n"
    "Be concise but thorough. This description will be used for search retrieval."
)


def describe_image(png_bytes: bytes, page: int | None, llm: LLMService) -> str:
    """
    Send a PNG image to the vision LLM and return a text description.

    Falls back to a generic placeholder on error.
    """
    fallback = f"Image from document (page {page})" if page else "Image from document"
    try:
        b64 = base64.b64encode(png_bytes).decode("utf-8")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": DESCRIBE_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ]
        description = llm.chat_completion(messages=messages, max_tokens=500)
        if description and description.strip():
            return description.strip()
        return fallback
    except Exception:
        logger.warning("Image description failed (page %s), using fallback", page, exc_info=True)
        return fallback
