import httpx
from app.config import get_settings


class SupabaseService:
    def __init__(self):
        settings = get_settings()
        self.base_url = f"{settings.supabase_url}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | list | None = None,
    ) -> dict | list | None:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}/{endpoint}",
                headers=self.headers,
                params=params,
                json=json,
            )
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()

    # ==================== Threads ====================

    async def create_thread(self, user_id: str, title: str | None = None) -> dict:
        result = await self._request(
            "POST",
            "threads",
            json={
                "user_id": user_id,
                "title": title,
            },
        )
        return result[0] if isinstance(result, list) else result

    async def get_threads(self, user_id: str) -> list[dict]:
        result = await self._request(
            "GET",
            "threads",
            params={
                "user_id": f"eq.{user_id}",
                "order": "created_at.desc",
            },
        )
        return result if isinstance(result, list) else []

    async def get_thread(self, thread_id: str, user_id: str) -> dict | None:
        result = await self._request(
            "GET",
            "threads",
            params={
                "id": f"eq.{thread_id}",
                "user_id": f"eq.{user_id}",
            },
        )
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    async def update_thread(
        self, thread_id: str, user_id: str, title: str
    ) -> dict | None:
        result = await self._request(
            "PATCH",
            "threads",
            params={
                "id": f"eq.{thread_id}",
                "user_id": f"eq.{user_id}",
            },
            json={"title": title, "updated_at": "now()"},
        )
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    async def delete_thread(self, thread_id: str, user_id: str) -> None:
        await self._request(
            "DELETE",
            "threads",
            params={
                "id": f"eq.{thread_id}",
                "user_id": f"eq.{user_id}",
            },
        )

    # ==================== Messages ====================

    async def create_message(
        self,
        thread_id: str,
        role: str,
        content: str,
    ) -> dict:
        result = await self._request(
            "POST",
            "messages",
            json={
                "thread_id": thread_id,
                "role": role,
                "content": content,
            },
        )
        return result[0] if isinstance(result, list) else result

    async def get_messages(self, thread_id: str) -> list[dict]:
        result = await self._request(
            "GET",
            "messages",
            params={
                "thread_id": f"eq.{thread_id}",
                "order": "created_at.asc",
            },
        )
        return result if isinstance(result, list) else []

    # ==================== Documents ====================

    async def create_document(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> dict:
        result = await self._request(
            "POST",
            "documents",
            json={
                "user_id": user_id,
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "storage_path": storage_path,
                "status": "pending",
            },
        )
        return result[0] if isinstance(result, list) else result

    async def get_documents(self, user_id: str) -> list[dict]:
        result = await self._request(
            "GET",
            "documents",
            params={
                "user_id": f"eq.{user_id}",
                "order": "created_at.desc",
            },
        )
        return result if isinstance(result, list) else []

    async def get_document(self, document_id: str, user_id: str) -> dict | None:
        result = await self._request(
            "GET",
            "documents",
            params={
                "id": f"eq.{document_id}",
                "user_id": f"eq.{user_id}",
            },
        )
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    async def update_document_status(
        self,
        document_id: str,
        status: str,
        error_message: str | None = None,
        chunk_count: int | None = None,
    ) -> dict | None:
        data = {"status": status, "updated_at": "now()"}
        if error_message is not None:
            data["error_message"] = error_message
        if chunk_count is not None:
            data["chunk_count"] = chunk_count

        result = await self._request(
            "PATCH",
            "documents",
            params={"id": f"eq.{document_id}"},
            json=data,
        )
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    async def delete_document(self, document_id: str, user_id: str) -> None:
        await self._request(
            "DELETE",
            "documents",
            params={
                "id": f"eq.{document_id}",
                "user_id": f"eq.{user_id}",
            },
        )

    # ==================== Chunks ====================

    async def create_chunks(self, chunks: list[dict]) -> list[dict]:
        """
        Bulk insert chunks with embeddings.

        Each chunk dict should have:
        - document_id: str
        - content: str
        - chunk_index: int
        - embedding: list[float] (1536 dimensions)
        - metadata: dict (optional)
        """
        result = await self._request("POST", "chunks", json=chunks)
        return result if isinstance(result, list) else []

    async def delete_chunks_by_document(self, document_id: str) -> None:
        await self._request(
            "DELETE",
            "chunks",
            params={"document_id": f"eq.{document_id}"},
        )

    async def search_chunks(
        self,
        user_id: str,
        embedding: list[float],
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[dict]:
        """
        Vector similarity search for relevant chunks.

        Uses Supabase's RPC to call a postgres function for vector search.
        """
        settings = get_settings()

        # Use RPC endpoint for vector search
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.supabase_url}/rest/v1/rpc/search_chunks",
                headers=self.headers,
                json={
                    "query_embedding": embedding,
                    "match_count": limit,
                    "match_threshold": threshold,
                    "filter_user_id": user_id,
                },
            )
            response.raise_for_status()
            return response.json()


def get_supabase_service() -> SupabaseService:
    return SupabaseService()
