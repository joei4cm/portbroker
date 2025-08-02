from fastapi import APIRouter

from app.api.v1 import anthropic, chat, providers

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/v1", tags=["openai"])
api_router.include_router(
    anthropic.router, prefix="/api/anthropic/v1", tags=["anthropic"]
)
api_router.include_router(providers.router, prefix="/admin", tags=["admin"])
