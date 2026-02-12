import logging

from app.services.embedding_service import EmbeddingService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        supabase: SupabaseService,
    ):
        self.embedding_service = embedding_service
        self.supabase = supabase

    async def retrieve(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        1. Embed the query
        2. Vector similarity search against user's chunks
        3. Enrich with document filenames
        4. Return matching chunks with scores

        Returns list of dicts with: content, similarity, document_id, filename, chunk_index
        """
        # Embed the query
        query_embedding = await self.embedding_service.embed_text(query)

        # Search for similar chunks
        results = await self.supabase.search_chunks(
            user_id=user_id,
            embedding=query_embedding,
            limit=limit,
            threshold=threshold,
        )

        if not results:
            logger.info("No chunks found for query (user=%s)", user_id)
            return []

        # Enrich with filenames from documents table
        doc_ids = list({r["document_id"] for r in results})
        doc_map = {}
        for doc_id in doc_ids:
            doc = await self.supabase.get_document(doc_id, user_id)
            if doc:
                doc_map[doc_id] = doc["filename"]

        for result in results:
            result["filename"] = doc_map.get(result["document_id"], "Unknown")

        logger.info(
            "Retrieved %d chunks for query (user=%s, threshold=%.2f)",
            len(results),
            user_id,
            threshold,
        )

        return results


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the system prompt."""
    if not chunks:
        return ""

    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("filename", "Unknown")
        content = chunk.get("content", "")
        similarity = chunk.get("similarity", 0)
        parts.append(f"[Source {i}: {source} (relevance: {similarity:.2f})]\n{content}")

    return "\n\n---\n\n".join(parts)
