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

    # Retrieval
    retrieval_threshold: float = 0.3
    retrieval_limit: int = 10
    query_rewrite_enabled: bool = True

    # Hybrid Search
    search_mode: str = "hybrid"  # "vector" | "keyword" | "hybrid"
    hybrid_alpha: float = 0.5  # 0.0 = keyword only, 1.0 = vector only
    rrf_k: int = 60  # RRF constant
    hybrid_candidate_limit: int = 20  # candidates per search type before fusion

    # Reranking (Cohere)
    rerank_enabled: bool = False
    rerank_api_key: str = ""
    rerank_model: str = "rerank-v3.5"
    rerank_top_n: int = 5

    # Image Descriptions (vision LLM during ingestion)
    image_description_enabled: bool = True
    image_similarity_min_ratio: float = 0.6  # image chunk must score ≥ 60% of top chunk
    image_max_results: int = 3  # max images per retrieval

    # Web Search (Tavily)
    tavily_api_key: str = ""

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
