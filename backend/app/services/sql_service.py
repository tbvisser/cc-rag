"""Text-to-SQL service: generates and executes read-only SQL from natural language."""

import json
import logging

import httpx

from app.config import get_settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

SCHEMA_DESCRIPTION = """You have access to a PostgreSQL database with these tables:

TABLE documents (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  filename TEXT NOT NULL,
  file_type TEXT,             -- MIME type e.g. 'application/pdf'
  file_size BIGINT,           -- bytes
  status TEXT,                -- 'pending', 'processing', 'completed', 'failed'
  chunk_count INTEGER DEFAULT 0,
  content_hash TEXT,
  metadata JSONB,             -- extracted metadata with keys: title, summary, topics (text[]), document_type, language, entities (object[])
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

TABLE chunks (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  chunk_index INTEGER,
  metadata JSONB,             -- chunk-level metadata, may include: page, section, topics
  embedding vector(1536),
  created_at TIMESTAMPTZ
)

IMPORTANT:
- Always filter by user_id = '{user_id}' to only access the current user's data.
- Use JSONB operators: metadata->>'key' for text, metadata->'key' for nested JSON, metadata @> '{{...}}'::jsonb for containment.
- For arrays inside JSONB (like topics), use jsonb_array_elements_text(metadata->'topics').
- Return only SELECT statements. No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or TRUNCATE.
"""

FORBIDDEN_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"}


class SQLService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def _validate_query(self, query: str) -> str | None:
        """Validate that the query is a safe SELECT. Returns error message or None."""
        stripped = query.strip().rstrip(";").strip()
        if not stripped.upper().startswith("SELECT"):
            return "Only SELECT queries are allowed."

        upper = stripped.upper()
        for kw in FORBIDDEN_KEYWORDS:
            # Check for keyword as a word boundary
            if f" {kw} " in f" {upper} ":
                return f"Forbidden keyword: {kw}"

        return None

    async def execute(self, question: str, user_id: str) -> str:
        """
        Generate SQL from a natural language question and execute it.

        Returns a formatted string with the SQL query and results.
        """
        # Step 1: Generate SQL
        schema = SCHEMA_DESCRIPTION.replace("{user_id}", user_id)
        prompt = (
            f"{schema}\n\n"
            "Generate a single PostgreSQL SELECT query that answers the following question. "
            "Return ONLY the SQL query, no explanation, no markdown code fences.\n\n"
            f"Question: {question}"
        )

        try:
            sql = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
        except Exception as e:
            logger.error("SQL generation failed: %s", e)
            return f"Failed to generate SQL query: {e}"

        # Clean up: remove markdown fences if present
        sql = sql.strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            sql = "\n".join(lines).strip()

        # Step 2: Validate
        error = self._validate_query(sql)
        if error:
            return f"Generated query was rejected: {error}\nQuery: {sql}"

        # Step 3: Execute via Supabase RPC
        settings = get_settings()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.supabase_url}/rest/v1/rpc/execute_readonly_sql",
                    headers={
                        "apikey": settings.supabase_service_key,
                        "Authorization": f"Bearer {settings.supabase_service_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query_text": sql,
                        "filter_user_id": user_id,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                rows = response.json()
        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response else ""
            logger.error("SQL execution failed: %s — %s", e, body)
            return f"SQL execution failed: {body}"
        except Exception as e:
            logger.error("SQL execution failed: %s", e)
            return f"SQL execution failed: {e}"

        # Step 4: Format results
        if not rows:
            return f"Query: {sql}\n\nNo results found."

        # Truncate to 50 rows
        truncated = len(rows) > 50
        rows = rows[:50]

        result_str = json.dumps(rows, indent=2, default=str)
        output = f"Query: {sql}\n\nResults ({len(rows)}{'+' if truncated else ''} rows):\n{result_str}"
        return output
