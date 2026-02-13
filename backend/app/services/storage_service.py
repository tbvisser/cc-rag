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
        """Create the documents bucket if it doesn't exist, or update its config."""
        bucket_config = {
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
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/html",
            ],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/bucket",
                headers={**self.headers, "Content-Type": "application/json"},
                json=bucket_config,
            )
            if response.status_code == 400:
                # Bucket already exists — update its config to pick up new MIME types
                await client.put(
                    f"{self.base_url}/bucket/documents",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json={
                        "public": bucket_config["public"],
                        "file_size_limit": bucket_config["file_size_limit"],
                        "allowed_mime_types": bucket_config["allowed_mime_types"],
                    },
                )
            elif response.status_code not in (200, 201):
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
            # 400/404 means file already deleted or path invalid - that's fine
            if response.status_code not in (400, 404):
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

    # ==================== Document Images ====================

    async def ensure_images_bucket(self) -> None:
        """Create the document-images bucket if it doesn't exist."""
        bucket_config = {
            "id": "document-images",
            "name": "document-images",
            "public": False,
            "file_size_limit": 10485760,  # 10MB
            "allowed_mime_types": ["image/png", "image/jpeg"],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/bucket",
                headers={**self.headers, "Content-Type": "application/json"},
                json=bucket_config,
            )
            if response.status_code == 400:
                await client.put(
                    f"{self.base_url}/bucket/document-images",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json={
                        "public": bucket_config["public"],
                        "file_size_limit": bucket_config["file_size_limit"],
                        "allowed_mime_types": bucket_config["allowed_mime_types"],
                    },
                )
            elif response.status_code not in (200, 201):
                response.raise_for_status()

    async def upload_image(
        self, user_id: str, document_id: str, image_name: str, content: bytes, content_type: str
    ) -> str:
        """Upload a document image to Supabase Storage. Returns the storage path."""
        storage_path = f"{user_id}/{document_id}/{image_name}"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/object/document-images/{storage_path}",
                headers={
                    **self.headers,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
                content=content,
            )
            response.raise_for_status()
        return storage_path

    async def download_image(self, storage_path: str) -> bytes:
        """Download a document image from Supabase Storage."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/object/document-images/{storage_path}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.content

    # ==================== Chat Images ====================

    async def ensure_chat_images_bucket(self) -> None:
        """Create the chat-images bucket if it doesn't exist."""
        bucket_config = {
            "id": "chat-images",
            "name": "chat-images",
            "public": False,
            "file_size_limit": 10485760,  # 10MB
            "allowed_mime_types": ["image/png", "image/jpeg", "image/gif", "image/webp"],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/bucket",
                headers={**self.headers, "Content-Type": "application/json"},
                json=bucket_config,
            )
            if response.status_code == 400:
                await client.put(
                    f"{self.base_url}/bucket/chat-images",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json={
                        "public": bucket_config["public"],
                        "file_size_limit": bucket_config["file_size_limit"],
                        "allowed_mime_types": bucket_config["allowed_mime_types"],
                    },
                )
            elif response.status_code not in (200, 201):
                response.raise_for_status()

    async def upload_chat_image(
        self, user_id: str, thread_id: str, image_name: str, content: bytes, content_type: str
    ) -> str:
        """Upload a chat image to Supabase Storage. Returns the storage path."""
        storage_path = f"{user_id}/{thread_id}/{image_name}"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/object/chat-images/{storage_path}",
                headers={
                    **self.headers,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
                content=content,
            )
            response.raise_for_status()
        return storage_path

    async def download_chat_image(self, storage_path: str) -> bytes:
        """Download a chat image from Supabase Storage."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/object/chat-images/{storage_path}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.content


def get_storage_service() -> StorageService:
    return StorageService()
