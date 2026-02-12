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


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime
