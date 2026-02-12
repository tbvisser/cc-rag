import httpx
from app.config import get_settings


class StorageService:
    def __init__(self):
        settings = get_settings()
        self.base_url = f"{settings.supabase_url}/storage/v1"
        self.headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
        }

    async def ensure_bucket(self) -> None:
        """Create the documents bucket if it doesn't exist."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/bucket",
                headers={**self.headers, "Content-Type": "application/json"},
                json={
                    "id": "documents",
                    "name": "documents",
                    "public": False,
                    "file_size_limit": 52428800,  # 50MB
                    "allowed_mime_types": [
                        "text/plain",
                        "text/markdown",
                        "text/csv",
                        "application/pdf",
                        "application/json",
                    ],
                },
            )
            # 400 means bucket already exists - that's fine
            if response.status_code not in (200, 201, 400):
                response.raise_for_status()

    async def upload_file(
        self, user_id: str, filename: str, content: bytes, content_type: str
    ) -> str:
        """Upload a file to Supabase Storage. Returns the storage path."""
        storage_path = f"{user_id}/{filename}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/object/documents/{storage_path}",
                headers={
                    **self.headers,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
                content=content,
            )
            response.raise_for_status()

        return storage_path

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from Supabase Storage."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/object/documents/{storage_path}",
                headers=self.headers,
            )
            # 404 means file already deleted - that's fine
            if response.status_code != 404:
                response.raise_for_status()

    async def download_file(self, storage_path: str) -> bytes:
        """Download a file from Supabase Storage."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/object/documents/{storage_path}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.content


def get_storage_service() -> StorageService:
    return StorageService()
