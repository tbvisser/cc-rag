import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, chat, documents, settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RAG Masterclass API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Duplicate"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(settings.router, prefix="/api", tags=["settings"])


@app.on_event("startup")
async def apply_saved_settings():
    """Apply user settings from JSON file on startup if it exists."""
    from app.api.routes.settings import _load_settings, _apply_settings, SETTINGS_FILE
    if SETTINGS_FILE.exists():
        _apply_settings(_load_settings())


@app.on_event("startup")
async def ensure_storage_buckets():
    """Create storage buckets on startup if they don't exist."""
    from app.services.storage_service import StorageService
    storage = StorageService()
    await storage.ensure_images_bucket()
    await storage.ensure_chat_images_bucket()
