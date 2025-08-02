import json
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import Provider
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse
from app.services.translation import TranslationService


class ProviderService:

    @staticmethod
    async def get_active_providers(db: AsyncSession) -> List[Provider]:
        result = await db.execute(
            select(Provider)
            .where(Provider.is_active == True)
            .order_by(Provider.priority.desc())
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
                "small_model": provider.small_model,
                "medium_model": provider.medium_model,
                "big_model": provider.big_model,
            },
        )

        request.model = mapped_model

        request_data = request.model_dump(exclude_none=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
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
        db: AsyncSession, request: ChatCompletionRequest, stream: bool = False
    ) -> Dict[str, Any]:
        providers = await ProviderService.get_active_providers(db)

        if not providers:
            raise Exception("No active providers available")

        last_error = None

        for provider in providers:
            try:
                return await ProviderService.call_provider_api(
                    provider, request, stream
                )
            except Exception as e:
                last_error = e
                continue

        raise Exception(f"All providers failed. Last error: {last_error}")
