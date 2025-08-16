from typing import Any, Dict, List, Optional

import httpx
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import Provider
from app.schemas.openai import ChatCompletionRequest
from app.services.translation import TranslationService


class ProviderService:

    @staticmethod
    async def get_active_providers(db: AsyncSession) -> List[Provider]:
        result = await db.execute(
            select(Provider)
            .where(Provider.is_active.is_(True))
            .order_by(Provider.name.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_provider_by_id(
        db: AsyncSession, provider_id: int
    ) -> Optional[Provider]:
        result = await db.execute(select(Provider).where(Provider.id == provider_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def call_provider_api(
        provider: Provider, request: ChatCompletionRequest, stream: bool = False
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider.api_key}",
        }

        if provider.headers:
            headers.update(provider.headers)

        mapped_model = TranslationService.map_claude_model_to_provider_model(
            request.model,
            {
                "model_list": provider.model_list,
                "small_model": provider.small_model,
                "medium_model": provider.medium_model,
                "big_model": provider.big_model,
            },
        )

        request.model = mapped_model

        request_data = request.model_dump(exclude_none=True)

        async with httpx.AsyncClient(
            timeout=300.0, verify=provider.verify_ssl
        ) as client:
            if stream:
                response = await client.post(
                    f"{provider.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=request_data,
                    stream=True,
                )
                return response
            else:
                response = await client.post(
                    f"{provider.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=request_data,
                )
                response.raise_for_status()
                return response.json()

    @staticmethod
    async def try_providers_until_success(
        db: AsyncSession, request: ChatCompletionRequest, stream: bool = False, fastapi_request: Optional[Request] = None
    ) -> Dict[str, Any]:
        providers = await ProviderService.get_active_providers(db)

        if not providers:
            raise Exception("No active providers available")

        last_error = None

        for provider in providers:
            try:
                # Store provider info in FastAPI request state for tracking
                if fastapi_request:
                    fastapi_request.state.provider_info = {
                        "id": provider.id,
                        "name": provider.name
                    }
                    fastapi_request.state.model_info = {
                        "requested": request.model,
                        "tier": "medium"  # Default, could be enhanced based on model mapping
                    }
                
                response = await ProviderService.call_provider_api(
                    provider, request, stream
                )
                
                # Update model info with actual model used
                if fastapi_request and hasattr(fastapi_request.state, 'model_info'):
                    mapped_model = provider.medium_model or "unknown"
                    fastapi_request.state.model_info["actual"] = mapped_model
                
                return response
            except Exception as e:
                last_error = e
                continue

        raise Exception(f"All providers failed. Last error: {last_error}")
