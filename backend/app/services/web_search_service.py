"""Web search service using Tavily API (raw httpx, no SDK)."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class WebSearchService:
    async def search(self, query: str, max_results: int = 5) -> str:
        """
        Search the web using Tavily API.

        Returns a formatted string with titles, URLs, and snippets.
        """
        settings = get_settings()

        if not settings.tavily_api_key:
            return "Web search is not configured. Please add a Tavily API key in Settings."

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    TAVILY_SEARCH_URL,
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_answer": False,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response else ""
            logger.error("Tavily search failed: %s — %s", e, body)
            return f"Web search failed: {body}"
        except Exception as e:
            logger.error("Tavily search failed: %s", e)
            return f"Web search failed: {e}"

        results = data.get("results", [])
        if not results:
            return "No web results found."

        parts = []
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            snippet = r.get("content", "")
            parts.append(f"**{title}**\nURL: {url}\n{snippet}")

        return "\n\n---\n\n".join(parts)
