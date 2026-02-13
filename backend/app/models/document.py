from typing import Any

from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    storage_path: str
    status: str
    error_message: str | None = None
    chunk_count: int | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
