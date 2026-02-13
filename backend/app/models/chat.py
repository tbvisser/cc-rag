from typing import Any
from pydantic import BaseModel
from datetime import datetime


class ThreadCreate(BaseModel):
    pass


class ThreadResponse(BaseModel):
    id: str
    user_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class ThreadWithMessages(ThreadResponse):
    messages: list["MessageResponse"]


class Attachment(BaseModel):
    type: str  # "image"
    url: str   # serving URL like "/api/threads/{id}/images/{name}"
    storage_path: str  # internal path for storage


class MessageCreate(BaseModel):
    content: str
    metadata_filter: dict[str, Any] | None = None
    attachments: list[Attachment] | None = None


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    attachments: list[dict] | None = None
    created_at: datetime
