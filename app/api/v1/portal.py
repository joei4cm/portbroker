from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin_user, get_current_portal_user, login_for_access_token
from app.core.database import get_db
from app.models.strategy import APIKey, Provider
from app.schemas.provider import APIKey as APIKeySchema, APIKeyAutoCreate, ProviderCreate, Provider as ProviderSchema
from app.utils.api_key_generator import (
    generate_expiration_date,
    generate_openai_style_api_key,
)

router = APIRouter()


class LoginRequest(BaseModel):
    api_key: str


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login to portal using API key and return JWT token"""
    return await login_for_access_token(request.api_key, db)


@router.get("/api-keys", response_model=List[APIKeySchema])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """List all API keys (accessible by authenticated portal users)"""
    result = await db.execute(select(APIKey))
    keys = result.scalars().all()
    return keys


@router.get("/api-keys/{key_id}", response_model=APIKeySchema)
async def get_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get a specific API key by ID"""
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
    """Create a new API key (admin only)"""
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


@router.put("/api-keys/{key_id}", response_model=APIKeySchema)
async def update_api_key(
    key_id: int,
    key_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Update an existing API key (admin only)"""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # If regenerating key, create new key
    if key_data.get("regenerate"):
        generated_key = generate_openai_style_api_key()
        api_key.api_key = generated_key

    # Update other fields
    for field, value in key_data.items():
        if field != "regenerate" and value is not None:
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
    """Delete an API key (admin only)"""
    result = await db.execute(delete(APIKey).where(APIKey.id == key_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.commit()
    return {"detail": "API key deleted successfully"}


@router.get("/user-info")
async def get_user_info(current_user: dict = Depends(get_current_portal_user)):
    """Get current user information"""
    return current_user


@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_admin_user)):
    """Get system settings"""
    from app.core.config import settings
    
    return {
        "database_type": settings.database_type,
        "database_url": settings.database_url,
        "host": settings.host,
        "port": settings.port,
        "default_openai_base_url": settings.default_openai_base_url,
        "default_big_model": settings.default_big_model,
        "default_small_model": settings.default_small_model,
    }


@router.put("/settings")
async def update_settings(
    settings_data: dict,
    current_user: dict = Depends(get_current_admin_user),
):
    """Update system settings"""
    # Note: In a real implementation, you would update the settings
    # For now, just return success
    return {"detail": "Settings updated successfully"}


@router.get("/providers", response_model=List[ProviderSchema])
async def get_providers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all providers for portal users"""
    result = await db.execute(select(Provider))
    providers = result.scalars().all()
    return providers


@router.post("/providers", response_model=ProviderSchema, status_code=201)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
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
    provider_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Update a provider (admin only)"""
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check for duplicate name if name is being updated
    if "name" in provider_data:
        result = await db.execute(
            select(Provider).where(
                Provider.name == provider_data["name"],
                Provider.id != provider_id
            )
        )
        existing_provider = result.scalar_one_or_none()
        if existing_provider:
            raise HTTPException(status_code=400, detail=f"Provider with name '{provider_data['name']}' already exists")
    
    # Update fields
    for field, value in provider_data.items():
        if value is not None:
            setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider
