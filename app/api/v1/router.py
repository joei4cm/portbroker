from fastapi import APIRouter

from app.api.v1 import anthropic, api_keys, chat, providers, providers_v1, strategies

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/v1", tags=["openai"])
api_router.include_router(
    anthropic.router, prefix="/api/anthropic/v1", tags=["anthropic"]
)
api_router.include_router(api_keys.router, prefix="/v1", tags=["api-keys"])
api_router.include_router(providers_v1.router, prefix="/v1", tags=["providers"])
api_router.include_router(providers.router, prefix="/portal", tags=["portal"])
api_router.include_router(strategies.router, prefix="/portal", tags=["strategies"])
