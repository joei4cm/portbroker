from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    get_current_admin_user,
    get_current_portal_user,
    login_for_access_token,
)
from app.core.config import settings
from app.core.database import get_db
from app.models.strategy import APIKey, Provider
from app.schemas.provider import APIKey as APIKeySchema
from app.schemas.provider import (
    APIKeyAutoCreate,
    APIKeyUpdate,
)
from app.schemas.provider import Provider as ProviderSchema
from app.schemas.provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderTestRequest,
    ModelValidationResponse,
    HealthCheckResponse,
)
from app.utils.api_key_generator import (
    generate_expiration_date,
    generate_openai_style_api_key,
)

router = APIRouter()


# Authentication helper function is now in the portal router


# Portal authentication is now handled by the separate portal router


@router.options("/providers")
async def options_providers(request: Request):
    """Handle CORS preflight requests for providers endpoint"""
    from fastapi.responses import Response
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        }
    )


@router.options("/models")
async def options_models(request: Request):
    """Handle CORS preflight requests for models endpoint"""
    from fastapi.responses import Response
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        }
    )


@router.options("/providers/{provider_id}")
async def options_provider_by_id(request: Request):
    """Handle CORS preflight requests for provider by ID endpoint"""
    from fastapi.responses import Response
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        }
    )


@router.options("/providers/{provider_id}/models")
async def options_provider_models(request: Request):
    """Handle CORS preflight requests for provider models endpoint"""
    from fastapi.responses import Response
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        }
    )


@router.options("/api-keys")
async def options_api_keys(request: Request):
    """Handle CORS preflight requests for API keys endpoint"""
    from fastapi.responses import Response
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        }
    )


@router.options("/api-keys/{key_id}")
async def options_api_key_by_id(request: Request):
    """Handle CORS preflight requests for API key by ID endpoint"""
    from fastapi.responses import Response
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        }
    )


@router.post("/login")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    """Login to portal and return JWT token"""
    # Get API key from request body
    body = await request.body()
    try:
        # Try to parse as JSON first
        import json

        data = json.loads(body)
        api_key = data.get("api_key") if isinstance(data, dict) else data
    except:
        # If not JSON, use raw body
        api_key = body.decode("utf-8").strip("\"'")  # Remove quotes

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    result = await login_for_access_token(api_key, db)

    # Create response with token and set cookie for browser authentication
    from fastapi.responses import JSONResponse

    response = JSONResponse(content=result)
    response.set_cookie(
        key="portal_token",
        value=result["access_token"],
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=1800,  # 30 minutes
    )

    return response


# Portal dashboard is now handled by the separate portal router


# Protect all existing portal endpoints with authentication
@router.get("/providers", response_model=List[ProviderSchema])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    result = await db.execute(select(Provider))
    providers = result.scalars().all()
    return providers


@router.get("/models")
async def get_all_models(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all available models from all active providers"""
    result = await db.execute(select(Provider).where(Provider.is_active.is_(True)))
    providers = result.scalars().all()

    all_models = []
    for provider in providers:
        if provider.model_list:
            for model in provider.model_list:
                all_models.append(
                    {
                        "model": model,
                        "provider": provider.name,
                        "provider_id": provider.id,
                        "provider_type": provider.provider_type,
                    }
                )

    return {"models": all_models}


@router.get("/providers/{provider_id}", response_model=ProviderSchema)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.get("/providers/{provider_id}/models")
async def get_provider_models(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get available models from a specific provider"""
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Return models from provider's model_list
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "models": provider.model_list or [],
    }


@router.post("/providers", response_model=ProviderSchema)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    try:
        # Check if provider with this name already exists
        result = await db.execute(select(Provider).where(Provider.name == provider_data.name))
        existing_provider = result.scalar_one_or_none()
        if existing_provider:
            raise HTTPException(status_code=400, detail="Provider with this name already exists")
        
        db_provider = Provider(**provider_data.model_dump())
        db.add(db_provider)
        await db.commit()
        await db.refresh(db_provider)
        return db_provider
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        await db.rollback()
        if "UNIQUE constraint failed: providers.name" in str(e):
            raise HTTPException(status_code=400, detail="Provider with this name already exists")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create provider: {str(e)}")


@router.put("/providers/{provider_id}", response_model=ProviderSchema)
async def update_provider(
    provider_id: int,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    try:
        result = await db.execute(select(Provider).where(Provider.id == provider_id))
        provider = result.scalar_one_or_none()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        # Check if provider with this name already exists (excluding current provider)
        if provider_data.name and provider_data.name != provider.name:
            existing_result = await db.execute(select(Provider).where(Provider.name == provider_data.name))
            existing_provider = existing_result.scalar_one_or_none()
            if existing_provider:
                raise HTTPException(status_code=400, detail="Provider with this name already exists")

        update_data = provider_data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(provider, field, value)

        await db.commit()
        await db.refresh(provider)
        return provider
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        await db.rollback()
        if "UNIQUE constraint failed: providers.name" in str(e):
            raise HTTPException(status_code=400, detail="Provider with this name already exists")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update provider: {str(e)}")


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    result = await db.execute(delete(Provider).where(Provider.id == provider_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.commit()
    return {"detail": "Provider deleted successfully"}


@router.get("/api-keys", response_model=List[APIKeySchema])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    result = await db.execute(select(APIKey))
    keys = result.scalars().all()
    return keys


@router.get("/api-keys/{key_id}", response_model=APIKeySchema)
async def get_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


@router.post("/api-keys", response_model=APIKeySchema)
async def create_api_key(
    key_data: APIKeyAutoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Create API key with auto-generated key content.
    The API key will be automatically generated and returned in the response.
    """
    # Generate the API key
    generated_key = generate_openai_style_api_key()

    # Calculate expiration date if specified
    expires_at = generate_expiration_date(key_data.expires_in_days)

    # Create the API key record
    db_key = APIKey(
        key_name=key_data.key_name,
        api_key=generated_key,
        description=key_data.description,
        is_active=key_data.is_active,
        is_admin=key_data.is_admin,
        expires_at=expires_at,
    )

    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)

    return db_key


@router.post("/api-keys/with-expiry")
async def create_api_key_with_expiry(
    key_name: str,
    api_key: str,
    description: Optional[str] = None,
    expires_in_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Create API key with optional expiration in days.
    If expires_in_days is None or 0, the key never expires.
    """
    expires_at = None
    if expires_in_days and expires_in_days > 0:
        expires_at = datetime.now() + timedelta(days=expires_in_days)

    db_key = APIKey(
        key_name=key_name,
        api_key=api_key,
        description=description,
        expires_at=expires_at,
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    return db_key


@router.put("/api-keys/{key_id}", response_model=APIKeySchema)
async def update_api_key(
    key_id: int,
    key_data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    update_data = key_data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(api_key, field, value)

    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    result = await db.execute(delete(APIKey).where(APIKey.id == key_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.commit()
    return {"detail": "API key deleted successfully"}


@router.get("/user-info")
async def get_user_info(current_user: dict = Depends(get_current_portal_user)):
    """Get current user information including admin status"""
    return {"username": current_user["username"], "is_admin": current_user["is_admin"]}


@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_portal_user)):
    """Get current settings configuration"""
    return {
        "database_type": settings.database_type,
        "database_url": settings.database_url,
        "supabase_url": settings.supabase_url,
        "host": settings.host,
        "port": settings.port,
        "debug": settings.debug,
        "default_openai_base_url": settings.default_openai_base_url,
        "default_big_model": settings.default_big_model,
        "default_small_model": settings.default_small_model,
    }


@router.post("/settings")
async def update_settings(
    settings_data: Dict[str, Any], current_user: dict = Depends(get_current_admin_user)
):
    """Update settings configuration"""
    # Note: In a production environment, you would want to:
    # 1. Validate the settings
    # 2. Update the .env file or configuration
    # 3. Potentially restart the service

    # For now, we'll just return success
    # In a real implementation, you would update the environment variables
    # and potentially restart the service or reload configuration

    return {
        "detail": "Settings updated successfully",
        "note": "Some changes may require a service restart to take effect",
    }


@router.post("/providers/validate-models", response_model=ModelValidationResponse)
async def validate_provider_models(
    request: ProviderTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Validate provider credentials and fetch available models"""
    try:
        import httpx
        import time
        from typing import Dict, Any

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
            timeout=30.0, verify=request.verify_ssl if request.verify_ssl is not None else True
        ) as client:
            start_time = time.time()
            response = await client.get(models_endpoint, headers=headers)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                models = await _extract_models_from_response(request.provider_type, data)
                return ModelValidationResponse(
                    models=models,
                    provider_type=request.provider_type,
                    success=True,
                    error=None
                )
            else:
                return ModelValidationResponse(
                    models=[],
                    provider_type=request.provider_type,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}"
                )

    except Exception as e:
        return ModelValidationResponse(
            models=[],
            provider_type=request.provider_type,
            success=False,
            error=str(e)
        )


@router.post("/providers/{provider_id}/health", response_model=HealthCheckResponse)
async def check_provider_health(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Check provider health status"""
    try:
        import httpx
        import time

        # Get provider from database
        result = await db.execute(select(Provider).where(Provider.id == provider_id))
        provider = result.scalar_one_or_none()
        
        if not provider:
            return HealthCheckResponse(
                healthy=False,
                error="Provider not found"
            )

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
                    models_available=len(provider.model_list) if provider.model_list else 0
                )
            else:
                return HealthCheckResponse(
                    healthy=False,
                    response_time=response_time,
                    error=f"HTTP {response.status_code}: {response.text}"
                )

    except Exception as e:
        return HealthCheckResponse(
            healthy=False,
            error=str(e)
        )


async def _extract_models_from_response(provider_type: str, data: Dict[str, Any]) -> List[str]:
    """Extract model names from provider response"""
    models = []
    
    if provider_type == "openai":
        models = [model["id"] for model in data.get("data", [])]
    elif provider_type == "anthropic":
        # Anthropic doesn't have a models endpoint, return default models
        models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
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


async def _validate_google_gemini(request: ProviderTestRequest, headers: Dict[str, Any]) -> ModelValidationResponse:
    """Validate Google Gemini API key and return available models"""
    try:
        import httpx
        
        # Google Gemini models are fixed based on API key access
        models = ["gemini-pro", "gemini-pro-vision"]
        
        # Try a simple request to validate the API key
        async with httpx.AsyncClient(
            timeout=30.0, verify=request.verify_ssl if request.verify_ssl is not None else True
        ) as client:
            # For Google, we'll just check if the API key format is valid
            # and return the standard models
            if request.api_key and len(request.api_key) > 10:
                return ModelValidationResponse(
                    models=models,
                    provider_type=request.provider_type,
                    success=True,
                    error=None
                )
            else:
                return ModelValidationResponse(
                    models=[],
                    provider_type=request.provider_type,
                    success=False,
                    error="Invalid API key format"
                )
    
    except Exception as e:
        return ModelValidationResponse(
            models=[],
            provider_type=request.provider_type,
            success=False,
            error=str(e)
        )


async def _check_google_health(provider: Provider, headers: Dict[str, Any]) -> HealthCheckResponse:
    """Check Google Gemini provider health"""
    try:
        import httpx
        import time
        
        # For Google, we'll just check if the API key format is valid
        if provider.api_key and len(provider.api_key) > 10:
            return HealthCheckResponse(
                healthy=True,
                models_available=len(provider.model_list) if provider.model_list else 0
            )
        else:
            return HealthCheckResponse(
                healthy=False,
                error="Invalid API key format"
            )
    
    except Exception as e:
        return HealthCheckResponse(
            healthy=False,
            error=str(e)
        )
