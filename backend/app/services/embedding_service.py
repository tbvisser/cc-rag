import os
from openai import AsyncOpenAI
from app.config import get_settings

# Max chunks per embedding API call
BATCH_SIZE = 100


def _make_async_openai_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client with optional LangSmith tracing."""
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_api_base,
    )

    if settings.langsmith_api_key:
        try:
            from langsmith.wrappers import wrap_openai
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
            os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langsmith_endpoint)
            os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
            os.environ.setdefault("LANGSMITH_WORKSPACE_ID", "21c7fb70-7c57-4f7f-bde7-de96cc8a855f")
            client = wrap_openai(client)
        except ImportError:
            pass

    return client


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        self.client = _make_async_openai_client()
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def embed_text(self, text: str) -> list[float]:
        """Get embedding for a single text string."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts, batching as needed."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = await self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            # Response data is in same order as input
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
