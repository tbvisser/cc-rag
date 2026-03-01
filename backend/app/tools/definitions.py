"""OpenAI function-calling tool definitions for the agent loop."""

from app.config import Settings


RETRIEVE_DOCUMENTS = {
    "type": "function",
    "function": {
        "name": "retrieve_documents",
        "description": (
            "Search the user's uploaded documents for relevant information. "
            "ALWAYS use this tool when the user asks ANY question that could relate to their documents. "
            "Do not skip retrieval and answer from your own knowledge. "
            "You can call this tool multiple times with different queries to find more information. "
            "Use specific keywords and noun phrases rather than full conversational questions as the query."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query using specific keywords or noun phrases (e.g. 'pricing tiers enterprise' "
                        "instead of 'what does it say about pricing?'). Be specific and focused."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}

TEXT_TO_SQL = {
    "type": "function",
    "function": {
        "name": "text_to_sql",
        "description": (
            "Query metadata about the user's documents using SQL. Use this for "
            "questions about document counts, types, topics, upload dates, or other "
            "aggregate/metadata questions. Do NOT use this for searching document content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question about document metadata (e.g. 'how many documents have I uploaded?', 'what topics are covered?').",
                }
            },
            "required": ["question"],
        },
    },
}

ANALYZE_DOCUMENT = {
    "type": "function",
    "function": {
        "name": "analyze_document",
        "description": (
            "Analyze an entire document in depth. Use this for questions that require "
            "understanding the full document such as summarization, identifying key themes, "
            "structural analysis, or comprehensive review. Do NOT use this for simple fact-finding "
            "— use retrieve_documents instead. Requires the exact filename."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The exact filename of the document to analyze (e.g. 'report.pdf').",
                },
                "question": {
                    "type": "string",
                    "description": "The question or analysis task to perform on the document.",
                },
            },
            "required": ["filename", "question"],
        },
    },
}

WEB_SEARCH = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information. Use this when the user asks "
            "about recent events, needs up-to-date information, or asks about topics "
            "not covered in their uploaded documents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The web search query.",
                }
            },
            "required": ["query"],
        },
    },
}


def get_enabled_tools(settings: Settings) -> list[dict]:
    """Return the list of active tool schemas based on configuration."""
    tools = [RETRIEVE_DOCUMENTS, TEXT_TO_SQL, ANALYZE_DOCUMENT]

    if settings.tavily_api_key:
        tools.append(WEB_SEARCH)

    return tools
