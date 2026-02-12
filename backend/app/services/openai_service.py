from typing import AsyncGenerator
from openai import OpenAI
from app.config import get_settings


class OpenAIService:
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)

    def create_thread(self) -> str:
        """Create a new OpenAI thread and return its ID."""
        thread = self.client.beta.threads.create()
        return thread.id

    def add_message(self, thread_id: str, content: str) -> str:
        """Add a user message to a thread and return the message ID."""
        message = self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )
        return message.id

    async def run_stream(
        self, thread_id: str, assistant_id: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Run the assistant on a thread and yield response chunks.

        For Module 1, we use the Responses API with a simple system prompt.
        In production, you'd use an actual assistant_id.
        """
        # For M1, we'll use chat completions with streaming since Assistants API
        # streaming is more complex. This simplifies the demo.
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)

        # Convert thread messages to chat format
        chat_messages = [
            {"role": "system", "content": "You are a helpful AI assistant."}
        ]
        for msg in reversed(list(messages.data)):
            content = msg.content[0].text.value if msg.content else ""
            chat_messages.append({"role": msg.role, "content": content})

        # Stream the response using chat completions
        stream = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_messages,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate_title(self, content: str) -> str:
        """Generate a short title for a conversation based on the first message."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Generate a very short title (3-5 words) for a conversation that starts with the following message. Return only the title, no quotes or punctuation.",
                },
                {"role": "user", "content": content},
            ],
            max_tokens=20,
        )
        return response.choices[0].message.content.strip()


def get_openai_service() -> OpenAIService:
    return OpenAIService()
