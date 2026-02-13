from pydantic import BaseModel


class ExtractedMetadata(BaseModel):
    title: str
    summary: str
    topics: list[str]
    document_type: str
    language: str
    key_entities: list[str]
