import logging
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"


class RerankingService:
    async def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_n: int | None = None,
    ) -> list[dict]:
        """
        Rerank chunks using Cohere's cross-encoder API.

        If no API key is configured, returns chunks unchanged.
        Adds `rerank_score` (0-1) to each returned chunk.
        """
        settings = get_settings()

        if not settings.rerank_enabled or not settings.rerank_api_key:
            logger.debug("Reranking skipped: not enabled or no API key")
            return chunks

        if not chunks:
            return []

        top_n = top_n or settings.rerank_top_n
        documents = [chunk["content"] for chunk in chunks]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    COHERE_RERANK_URL,
                    headers={
                        "Authorization": f"Bearer {settings.rerank_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.rerank_model,
                        "query": query,
                        "documents": documents,
                        "top_n": min(top_n, len(chunks)),
                    },
                )
                response.raise_for_status()
                data = response.json()

            reranked = []
            for result in data.get("results", []):
                idx = result["index"]
                chunk = chunks[idx].copy()
                chunk["rerank_score"] = result["relevance_score"]
                chunk["similarity"] = result["relevance_score"]
                reranked.append(chunk)

            logger.info(
                "Reranked %d -> %d chunks (model=%s)",
                len(chunks),
                len(reranked),
                settings.rerank_model,
            )
            return reranked

        except Exception as e:
            logger.warning("Reranking failed, returning original chunks: %s", e)
            return chunks
