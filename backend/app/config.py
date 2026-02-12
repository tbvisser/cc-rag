from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    # LLM (OpenAI-compatible API - works with OpenRouter, Ollama, LM Studio, etc.)
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # OpenAI Vector Store (Responses API file_search)
    openai_vector_store_id: str = ""

    # Embeddings
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimensions: int = 1536

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Observability
    langsmith_api_key: str = ""
    langsmith_endpoint: str = "https://eu.api.smith.langchain.com"
    langsmith_project: str = "rag-masterclass"

    # Legacy (kept for backwards compatibility during migration)
    openai_api_key: str = ""

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
