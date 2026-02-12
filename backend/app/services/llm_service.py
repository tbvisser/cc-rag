import os
from typing import AsyncGenerator
from openai import OpenAI
from app.config import get_settings


def _make_openai_client() -> OpenAI:
    """Create an OpenAI client with optional LangSmith tracing."""
    settings = get_settings()
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
    )

    # Wrap with LangSmith tracing if configured
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
            pass  # langsmith not installed, skip tracing

    return client


class LLMService:
    """
    Generic LLM service using OpenAI-compatible Chat Completions API.
    Works with OpenAI, OpenRouter, Ollama, LM Studio, etc.
    Automatically traced via LangSmith when configured.
    """

    def __init__(self):
        settings = get_settings()
        self.client = _make_openai_client()
        self.model = settings.llm_model

    async def chat_completion_stream(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
        """
        chat_messages = []

        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})

        chat_messages.extend(messages)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=chat_messages,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_completion(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Get a non-streaming chat completion response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            max_tokens: Optional max tokens limit
        """
        chat_messages = []

        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})

        chat_messages.extend(messages)

        kwargs = {
            "model": self.model,
            "messages": chat_messages,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()

    def generate_title(self, content: str) -> str:
        """Generate a short title for a conversation based on the first message."""
        return self.chat_completion(
            messages=[{"role": "user", "content": content}],
            system_prompt="Generate a very short title (3-5 words) for a conversation that starts with the following message. Return only the title, no quotes or punctuation.",
            max_tokens=20,
        )


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
