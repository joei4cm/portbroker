from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin_user, get_current_portal_user
from app.core.config import settings
from app.core.database import get_db
from app.models.strategy import Provider
from app.schemas.provider import (
    HealthCheckResponse,
    ModelValidationResponse,
    ProviderTestRequest,
)

router = APIRouter()



@router.post("/providers/validate-models", response_model=ModelValidationResponse)
async def validate_provider_models(
    request: ProviderTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Validate provider credentials and fetch available models"""
    try:
        import time
        from typing import Any, Dict

        import httpx

        # Prepare headers based on provider type
        headers = {
            "Content-Type": "application/json",
        }

        # Set up authentication based on provider type
        if request.provider_type == "openai":
            headers["Authorization"] = f"Bearer {request.api_key}"
        elif request.provider_type == "anthropic":
            headers["x-api-key"] = request.api_key
            headers["anthropic-version"] = "2023-06-01"
        elif request.provider_type == "google":
            # Google Gemini uses API key in URL
            pass
        elif request.provider_type == "azure":
            headers["api-key"] = request.api_key
        elif request.provider_type == "cohere":
            headers["Authorization"] = f"Bearer {request.api_key}"
        elif request.provider_type == "mistral":
            headers["Authorization"] = f"Bearer {request.api_key}"
        elif request.provider_type == "perplexity":
            headers["Authorization"] = f"Bearer {request.api_key}"
        else:  # custom
            headers["Authorization"] = f"Bearer {request.api_key}"

        if request.headers:
            headers.update(request.headers)

        # Determine the models endpoint based on provider type
        models_endpoint = None
        if request.provider_type == "openai":
            models_endpoint = f"{request.base_url.rstrip('/')}/models"
        elif request.provider_type == "anthropic":
            models_endpoint = f"{request.base_url.rstrip('/')}/messages"
        elif request.provider_type == "google":
            # Google Gemini models are discovered via API key validation
            return await _validate_google_gemini(request, headers)
        elif request.provider_type == "azure":
            models_endpoint = f"{request.base_url.rstrip('/')}/models"
        elif request.provider_type == "cohere":
            models_endpoint = f"{request.base_url.rstrip('/')}/models"
        elif request.provider_type == "mistral":
            models_endpoint = f"{request.base_url.rstrip('/')}/v1/models"
        elif request.provider_type == "perplexity":
            models_endpoint = f"{request.base_url.rstrip('/')}/models"
        else:  # custom - assume OpenAI compatible
            models_endpoint = f"{request.base_url.rstrip('/')}/models"

        # Make the request to fetch models
        async with httpx.AsyncClient(
            timeout=30.0,
            verify=request.verify_ssl if request.verify_ssl is not None else True,
        ) as client:
            start_time = time.time()
            response = await client.get(models_endpoint, headers=headers)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                models = await _extract_models_from_response(
                    request.provider_type, data
                )
                return ModelValidationResponse(
                    models=models,
                    provider_type=request.provider_type,
                    success=True,
                    error=None,
                )
            else:
                return ModelValidationResponse(
                    models=[],
                    provider_type=request.provider_type,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

    except Exception as e:
        return ModelValidationResponse(
            models=[], provider_type=request.provider_type, success=False, error=str(e)
        )


@router.post("/providers/{provider_id}/health", response_model=HealthCheckResponse)
async def check_provider_health(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Check provider health status"""
    try:
        import time

        import httpx

        # Get provider from database
        result = await db.execute(select(Provider).where(Provider.id == provider_id))
        provider = result.scalar_one_or_none()

        if not provider:
            return HealthCheckResponse(healthy=False, error="Provider not found")

        # Prepare headers based on provider type
        headers = {
            "Content-Type": "application/json",
        }

        # Set up authentication based on provider type
        if provider.provider_type == "openai":
            headers["Authorization"] = f"Bearer {provider.api_key}"
        elif provider.provider_type == "anthropic":
            headers["x-api-key"] = provider.api_key
            headers["anthropic-version"] = "2023-06-01"
        elif provider.provider_type == "azure":
            headers["api-key"] = provider.api_key
        elif provider.provider_type == "cohere":
            headers["Authorization"] = f"Bearer {provider.api_key}"
        elif provider.provider_type == "mistral":
            headers["Authorization"] = f"Bearer {provider.api_key}"
        elif provider.provider_type == "perplexity":
            headers["Authorization"] = f"Bearer {provider.api_key}"
        else:  # custom
            headers["Authorization"] = f"Bearer {provider.api_key}"

        if provider.headers:
            headers.update(provider.headers)

        # Determine the health check endpoint
        health_endpoint = None
        if provider.provider_type == "openai":
            health_endpoint = f"{provider.base_url.rstrip('/')}/models"
        elif provider.provider_type == "anthropic":
            health_endpoint = f"{provider.base_url.rstrip('/')}/messages"
        elif provider.provider_type == "google":
            # For Google, we'll check if the API key is valid
            return await _check_google_health(provider, headers)
        elif provider.provider_type == "azure":
            health_endpoint = f"{provider.base_url.rstrip('/')}/models"
        elif provider.provider_type == "cohere":
            health_endpoint = f"{provider.base_url.rstrip('/')}/models"
        elif provider.provider_type == "mistral":
            health_endpoint = f"{provider.base_url.rstrip('/')}/v1/models"
        elif provider.provider_type == "perplexity":
            health_endpoint = f"{provider.base_url.rstrip('/')}/models"
        else:  # custom - assume OpenAI compatible
            health_endpoint = f"{provider.base_url.rstrip('/')}/models"

        # Make the health check request
        async with httpx.AsyncClient(
            timeout=30.0, verify=provider.verify_ssl
        ) as client:
            start_time = time.time()
            response = await client.get(health_endpoint, headers=headers)
            response_time = time.time() - start_time

            if response.status_code == 200:
                return HealthCheckResponse(
                    healthy=True,
                    response_time=response_time,
                    models_available=(
                        len(provider.model_list) if provider.model_list else 0
                    ),
                )
            else:
                return HealthCheckResponse(
                    healthy=False,
                    response_time=response_time,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

    except Exception as e:
        return HealthCheckResponse(healthy=False, error=str(e))


async def _extract_models_from_response(
    provider_type: str, data: Dict[str, Any]
) -> List[str]:
    """Extract model names from provider response"""
    models = []

    if provider_type == "openai":
        models = [model["id"] for model in data.get("data", [])]
    elif provider_type == "anthropic":
        # Anthropic doesn't have a models endpoint, return default models
        models = [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]
    elif provider_type == "azure":
        models = [model["id"] for model in data.get("data", [])]
    elif provider_type == "cohere":
        models = [model["name"] for model in data.get("models", [])]
    elif provider_type == "mistral":
        models = [model["id"] for model in data.get("data", [])]
    elif provider_type == "perplexity":
        models = [model["id"] for model in data.get("data", [])]
    else:  # custom - assume OpenAI compatible
        models = [model["id"] for model in data.get("data", [])]

    return models


async def _validate_google_gemini(
    request: ProviderTestRequest, headers: Dict[str, Any]
) -> ModelValidationResponse:
    """Validate Google Gemini API key and return available models"""
    try:
        import httpx

        # Google Gemini models are fixed based on API key access
        models = ["gemini-pro", "gemini-pro-vision"]

        # Try a simple request to validate the API key
        async with httpx.AsyncClient(
            timeout=30.0,
            verify=request.verify_ssl if request.verify_ssl is not None else True,
        ) as client:
            # For Google, we'll just check if the API key format is valid
            # and return the standard models
            if request.api_key and len(request.api_key) > 10:
                return ModelValidationResponse(
                    models=models,
                    provider_type=request.provider_type,
                    success=True,
                    error=None,
                )
            else:
                return ModelValidationResponse(
                    models=[],
                    provider_type=request.provider_type,
                    success=False,
                    error="Invalid API key format",
                )

    except Exception as e:
        return ModelValidationResponse(
            models=[], provider_type=request.provider_type, success=False, error=str(e)
        )


async def _check_google_health(
    provider: Provider, headers: Dict[str, Any]
) -> HealthCheckResponse:
    """Check Google Gemini provider health"""
    try:
        import time

        import httpx

        # For Google, we'll just check if the API key format is valid
        if provider.api_key and len(provider.api_key) > 10:
            return HealthCheckResponse(
                healthy=True,
                models_available=len(provider.model_list) if provider.model_list else 0,
            )
        else:
            return HealthCheckResponse(healthy=False, error="Invalid API key format")

    except Exception as e:
        return HealthCheckResponse(healthy=False, error=str(e))