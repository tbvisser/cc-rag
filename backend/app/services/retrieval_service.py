import logging

from app.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.reranking_service import RerankingService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    alpha: float = 0.5,
    k: int = 60,
) -> list[dict]:
    """
    Combine vector and keyword search results using Reciprocal Rank Fusion.

    score(chunk) = alpha * 1/(k + vector_rank) + (1-alpha) * 1/(k + keyword_rank)

    Chunks appearing in both lists get naturally boosted.
    Deduplication via chunk ID as dict key.
    """
    alpha = max(0.0, min(1.0, alpha))
    fused: dict[str, dict] = {}

    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result["id"]
        if chunk_id not in fused:
            fused[chunk_id] = result.copy()
            fused[chunk_id]["similarity"] = 0.0
        fused[chunk_id]["similarity"] += alpha * (1.0 / (k + rank))

    for rank, result in enumerate(keyword_results, start=1):
        chunk_id = result["id"]
        if chunk_id not in fused:
            fused[chunk_id] = result.copy()
            fused[chunk_id]["similarity"] = 0.0
        fused[chunk_id]["similarity"] += (1.0 - alpha) * (1.0 / (k + rank))

    # Sort by fused score descending
    combined = sorted(fused.values(), key=lambda x: x["similarity"], reverse=True)
    return combined


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        supabase: SupabaseService,
    ):
        self.embedding_service = embedding_service
        self.supabase = supabase
        self.reranking_service = RerankingService()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
        threshold: float = 0.7,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        Supports three search modes:
        - "vector": embedding similarity only (original behavior)
        - "keyword": Postgres full-text search only
        - "hybrid": combines vector + keyword via Reciprocal Rank Fusion

        Optionally reranks results via Cohere cross-encoder API.
        """
        settings = get_settings()
        search_mode = settings.search_mode
        candidate_limit = settings.hybrid_candidate_limit

        vector_results = []
        keyword_results = []

        # Vector search
        if search_mode in ("vector", "hybrid"):
            query_embedding = await self.embedding_service.embed_text(query)
            vector_results = await self.supabase.search_chunks(
                user_id=user_id,
                embedding=query_embedding,
                limit=candidate_limit if search_mode == "hybrid" else limit,
                threshold=threshold,
                filter_metadata=metadata_filter,
            )

        # Keyword search
        if search_mode in ("keyword", "hybrid"):
            keyword_results = await self.supabase.search_chunks_keyword(
                user_id=user_id,
                query_text=query,
                limit=candidate_limit if search_mode == "hybrid" else limit,
            )

        # Combine results based on mode
        if search_mode == "hybrid":
            results = reciprocal_rank_fusion(
                vector_results=vector_results,
                keyword_results=keyword_results,
                alpha=settings.hybrid_alpha,
                k=settings.rrf_k,
            )
        elif search_mode == "keyword":
            # Map keyword 'rank' to 'similarity' for consistent downstream use
            for r in keyword_results:
                r["similarity"] = r.get("rank", 0.0)
            results = keyword_results
        else:
            results = vector_results

        # Rerank if enabled
        if settings.rerank_enabled:
            results = await self.reranking_service.rerank(
                query=query,
                chunks=results,
                top_n=settings.rerank_top_n,
            )

        # Trim to final limit
        results = results[:limit]

        if not results:
            logger.info("No chunks found for query (user=%s, mode=%s)", user_id, search_mode)
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
            "Retrieved %d chunks for query (user=%s, mode=%s, threshold=%.2f)",
            len(results),
            user_id,
            search_mode,
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
