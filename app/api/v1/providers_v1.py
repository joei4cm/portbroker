from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin_api_key, get_current_api_key
from app.core.database import get_db
from app.models.strategy import Provider
from app.schemas.provider import Provider as ProviderSchema
from app.schemas.provider import ProviderCreate, ProviderTestRequest, ProviderUpdate

router = APIRouter()

# Provider type configurations with default URLs
PROVIDER_CONFIGS = {
    "openai": {
        "default_url": "https://api.openai.com/v1",
        "models_endpoint": "/models",
        "name": "OpenAI",
    },
    "azure": {
        "default_url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment",
        "models_endpoint": "/models?api-version=2023-12-01-preview",
        "name": "Azure OpenAI",
    },
    "anthropic": {
        "default_url": "https://api.anthropic.com",
        "models_endpoint": "/v1/messages",
        "name": "Anthropic",
    },
    "gemini": {
        "default_url": "https://generativelanguage.googleapis.com/v1beta",
        "models_endpoint": "/models",
        "name": "Google Gemini",
    },
    "mistral": {
        "default_url": "https://api.mistral.ai/v1",
        "models_endpoint": "/models",
        "name": "Mistral AI",
    },
    "perplexity": {
        "default_url": "https://api.perplexity.ai",
        "models_endpoint": "/models",
        "name": "Perplexity",
    },
    "ollama": {
        "default_url": "http://localhost:11434",
        "models_endpoint": "/api/tags",
        "name": "Local Ollama",
    },
    "groq": {
        "default_url": "https://api.groq.com/openai/v1",
        "models_endpoint": "/models",
        "name": "Groq",
    },
    "openrouter": {
        "default_url": "https://openrouter.ai/api/v1",
        "models_endpoint": "/models",
        "name": "OpenRouter",
    },
    "custom": {"default_url": "", "models_endpoint": "/models", "name": "Custom"},
}


@router.get("/providers", response_model=List[ProviderSchema])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_api_key),
):
    """List all providers (authenticated users)"""
    result = await db.execute(select(Provider))
    providers = result.scalars().all()
    return providers


@router.get("/providers/{provider_id}", response_model=ProviderSchema)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_api_key),
):
    """Get a specific provider by ID (authenticated users)"""
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.get("/providers/{provider_id}/models")
async def get_provider_models(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_api_key),
):
    """Get available models from a specific provider (authenticated users)"""
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "models": provider.model_list or [],
    }


@router.post("/providers", response_model=ProviderSchema, status_code=201)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_admin_api_key),
):
    """Create a new provider (admin only)"""
    # Check for duplicate provider name
    result = await db.execute(select(Provider).where(Provider.name == provider_data.name))
    existing_provider = result.scalar_one_or_none()
    if existing_provider:
        raise HTTPException(status_code=400, detail=f"Provider with name '{provider_data.name}' already exists")
    
    db_provider = Provider(**provider_data.model_dump())
    db.add(db_provider)
    await db.commit()
    await db.refresh(db_provider)
    return db_provider


@router.put("/providers/{provider_id}", response_model=ProviderSchema)
async def update_provider(
    provider_id: int,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_admin_api_key),
):
    """Update a provider (admin only)"""
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = provider_data.model_dump(exclude_none=True)
    
    # Check for duplicate name if name is being updated
    if "name" in update_data:
        result = await db.execute(
            select(Provider).where(
                Provider.name == update_data["name"],
                Provider.id != provider_id
            )
        )
        existing_provider = result.scalar_one_or_none()
        if existing_provider:
            raise HTTPException(status_code=400, detail=f"Provider with name '{update_data['name']}' already exists")
    
    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_admin_api_key),
):
    """Delete a provider (admin only)"""
    result = await db.execute(delete(Provider).where(Provider.id == provider_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.commit()
    return {"detail": "Provider deleted successfully"}


@router.get("/provider-types")
async def get_provider_types():
    """Get available provider types with their default configurations"""
    provider_types = []
    for provider_type, config in PROVIDER_CONFIGS.items():
        provider_types.append(
            {
                "type": provider_type,
                "name": config["name"],
                "default_url": config["default_url"],
                "models_endpoint": config["models_endpoint"],
            }
        )
    return {"provider_types": provider_types}


@router.post("/providers/load-models")
async def load_provider_models(request: ProviderTestRequest):
    """Load models from a provider's API"""
    provider_type = request.provider_type
    base_url = request.base_url
    api_key = request.api_key
    headers = request.headers
    verify_ssl = request.verify_ssl

    if provider_type not in PROVIDER_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid provider type")

    config = PROVIDER_CONFIGS[provider_type]
    models_endpoint = config["models_endpoint"]

    # Prepare headers
    request_headers = {}
    if headers:
        request_headers.update(headers)

    # Add provider-specific authentication
    if provider_type == "openai":
        request_headers["Authorization"] = f"Bearer {api_key}"
    elif provider_type == "anthropic":
        request_headers["x-api-key"] = api_key
        request_headers["anthropic-version"] = "2023-06-01"
    elif provider_type == "azure":
        request_headers["api-key"] = api_key
    elif provider_type in ["gemini", "mistral", "perplexity", "groq", "openrouter"]:
        request_headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=verify_ssl) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}{models_endpoint}", headers=request_headers
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to load models: {response.text}",
                )

            data = response.json()

            # Parse models based on provider type
            models = []
            if provider_type == "openai":
                models = [model["id"] for model in data.get("data", [])]
            elif provider_type == "anthropic":
                # Anthropic doesn't have a models endpoint, use common models
                models = [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                    "claude-3-5-sonnet-20241022",
                ]
            elif provider_type == "ollama":
                models = [model["name"] for model in data.get("models", [])]
            elif provider_type == "gemini":
                models = [model["name"] for model in data.get("models", [])]
            else:
                # Generic OpenAI-compatible format
                models = [model["id"] for model in data.get("data", [])]

            return {
                "models": models,
                "provider_type": provider_type,
                "base_url": base_url,
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=408, detail="Request timeout while loading models"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading models: {str(e)}")


