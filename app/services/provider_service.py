import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import Provider
from app.schemas.openai import ChatCompletionRequest
# TranslationService is no longer needed here as model mapping is handled by strategy service

# Configure logging
logger = logging.getLogger(__name__)


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

        # Model mapping is now handled by the strategy service in the chat endpoint
        # Use the model as-is from the request
        original_model = request.model
        request_data = request.model_dump(exclude_none=True)

        # Log request details
        logger.info("=== PROVIDER REQUEST ===")
        logger.info(f"Provider: {provider.name} (ID: {provider.id})")
        logger.info(f"Model: {original_model}")
        logger.info(f"Stream: {stream}")
        logger.info(f"Request URL: {provider.base_url.rstrip('/')}/chat/completions")
        logger.info(f"Request headers: {json.dumps({k: v for k, v in headers.items() if k != 'Authorization'}, indent=2, ensure_ascii=False)}")
        logger.info(f"Request data: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
        logger.info(f"Request data length: {len(json.dumps(request_data, ensure_ascii=False))} characters")

        if stream:
            # For streaming, return a mock response that will be handled by the API endpoint
            logger.info("=== STREAMING MODE ===")
            return {"stream": True, "provider": provider, "headers": headers, "request_data": request_data}
        else:
            async with httpx.AsyncClient(
                timeout=300.0, verify=provider.verify_ssl
            ) as client:
                logger.info("=== SENDING REQUEST TO PROVIDER ===")
                logger.info(f"Full URL: {provider.base_url.rstrip('/')}/chat/completions")
                response = await client.post(
                    f"{provider.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=request_data,
                )
                logger.info(f"Provider response status: {response.status_code}")
                logger.info(f"Provider response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    error_text = await response.text()
                    logger.error(f"Provider returned non-200 status: {response.status_code}")
                    logger.error(f"Provider error response: {error_text}")
                    raise Exception(f"Provider returned status {response.status_code}: {error_text}")
                
                response_json = response.json()
                
                # Log response details
                logger.info("=== PROVIDER RESPONSE ===")
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                logger.info(f"Response data: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                logger.info(f"Response data length: {len(json.dumps(response_json, ensure_ascii=False))} characters")
                
                return response_json

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
                logger.error(f"Provider {provider.name} failed: {str(e)}")
                logger.error(f"Exception type: {type(e)}")
                last_error = e
                continue

        raise Exception(f"All providers failed. Last error: {last_error}")
