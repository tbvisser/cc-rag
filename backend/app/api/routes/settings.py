import json
from pathlib import Path
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app.api.middleware.auth import get_current_user, TokenPayload
from app.config import get_settings, Settings

router = APIRouter()

SETTINGS_FILE = Path(__file__).resolve().parents[3] / "user_settings.json"


class LLMConfig(BaseModel):
    model_name: str = ""
    base_url: str = ""
    api_key: str = ""


class EmbeddingConfig(BaseModel):
    model_name: str = ""
    base_url: str = ""
    api_key: str = ""
    dimensions: int = 1536


class RetrievalConfig(BaseModel):
    search_mode: str = "hybrid"  # "vector" | "keyword" | "hybrid"
    hybrid_alpha: float = 0.5
    rrf_k: int = 60
    hybrid_candidate_limit: int = 20
    rerank_enabled: bool = False
    rerank_api_key: str = ""
    rerank_model: str = "rerank-v3.5"

    @field_validator('hybrid_alpha')
    @classmethod
    def clamp_hybrid_alpha(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ToolsConfig(BaseModel):
    tavily_api_key: str = ""


class UserSettings(BaseModel):
    llm: LLMConfig = LLMConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    tools: ToolsConfig = ToolsConfig()


def _load_settings() -> UserSettings:
    """Load user settings from JSON file, falling back to env defaults."""
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text())
            return UserSettings(**data)
        except Exception:
            pass
    # Use a fresh Settings instance — NOT the cached singleton which
    # _apply_settings() may have modified in-place with stale values.
    fresh = Settings()
    return UserSettings(
        llm=LLMConfig(
            model_name=fresh.llm_model,
            base_url=fresh.llm_api_base,
            api_key=fresh.llm_api_key,
        ),
        embedding=EmbeddingConfig(
            model_name=fresh.embedding_model,
            base_url=fresh.embedding_api_base,
            api_key=fresh.embedding_api_key,
            dimensions=fresh.embedding_dimensions,
        ),
        retrieval=RetrievalConfig(
            search_mode=fresh.search_mode,
            hybrid_alpha=fresh.hybrid_alpha,
            rrf_k=fresh.rrf_k,
            hybrid_candidate_limit=fresh.hybrid_candidate_limit,
            rerank_enabled=fresh.rerank_enabled,
            rerank_api_key=fresh.rerank_api_key,
            rerank_model=fresh.rerank_model,
        ),
        tools=ToolsConfig(
            tavily_api_key=fresh.tavily_api_key,
        ),
    )


def _save_settings(user_settings: UserSettings) -> None:
    """Save user settings to JSON file and apply to running config."""
    SETTINGS_FILE.write_text(user_settings.model_dump_json(indent=2))
    _apply_settings(user_settings)


def _apply_settings(user_settings: UserSettings) -> None:
    """Apply user settings by reinitializing singleton services."""
    from app.config import get_settings as _get_settings

    # Clear the lru_cache so Settings re-reads
    _get_settings.cache_clear()
    settings = _get_settings()

    # Override the in-memory settings object
    if user_settings.llm.model_name:
        settings.llm_model = user_settings.llm.model_name
    if user_settings.llm.base_url:
        settings.llm_api_base = user_settings.llm.base_url
    if user_settings.llm.api_key:
        settings.llm_api_key = user_settings.llm.api_key
    if user_settings.embedding.model_name:
        settings.embedding_model = user_settings.embedding.model_name
    if user_settings.embedding.base_url:
        settings.embedding_api_base = user_settings.embedding.base_url
    if user_settings.embedding.api_key:
        settings.embedding_api_key = user_settings.embedding.api_key
    if user_settings.embedding.dimensions:
        settings.embedding_dimensions = user_settings.embedding.dimensions

    # Retrieval settings
    if user_settings.retrieval.search_mode:
        settings.search_mode = user_settings.retrieval.search_mode
    settings.hybrid_alpha = user_settings.retrieval.hybrid_alpha
    settings.rrf_k = user_settings.retrieval.rrf_k
    settings.hybrid_candidate_limit = user_settings.retrieval.hybrid_candidate_limit
    settings.rerank_enabled = user_settings.retrieval.rerank_enabled
    if user_settings.retrieval.rerank_api_key:
        settings.rerank_api_key = user_settings.retrieval.rerank_api_key
    if user_settings.retrieval.rerank_model:
        settings.rerank_model = user_settings.retrieval.rerank_model

    # Tools settings
    if user_settings.tools.tavily_api_key:
        settings.tavily_api_key = user_settings.tools.tavily_api_key

    # Reset singleton services so they pick up new config
    import app.services.llm_service as llm_mod
    llm_mod._llm_service = None

    # EmbeddingService is not cached as singleton, it re-reads settings each time


class SettingsResponse(BaseModel):
    llm: LLMConfig
    embedding: EmbeddingConfig
    retrieval: RetrievalConfig
    tools: ToolsConfig


@router.get("/settings", response_model=SettingsResponse)
async def get_user_settings(
    _user: TokenPayload = Depends(get_current_user),
):
    """Get current LLM, embedding, and retrieval configuration."""
    s = _load_settings()
    return SettingsResponse(
        llm=s.llm,
        embedding=s.embedding,
        retrieval=s.retrieval,
        tools=s.tools,
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_user_settings(
    payload: UserSettings,
    _user: TokenPayload = Depends(get_current_user),
):
    """Update LLM, embedding, retrieval, and tools configuration."""
    _save_settings(payload)
    s = _load_settings()
    return SettingsResponse(
        llm=s.llm,
        embedding=s.embedding,
        retrieval=s.retrieval,
        tools=s.tools,
    )
