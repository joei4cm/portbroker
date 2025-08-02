from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.provider import APIKey, Provider
from app.schemas.provider import APIKey as APIKeySchema
from app.schemas.provider import (
    APIKeyCreate,
    APIKeyAutoCreate,
    APIKeyUpdate,
)
from app.schemas.provider import Provider as ProviderSchema
from app.schemas.provider import (
    ProviderCreate,
    ProviderUpdate,
)
from app.utils.api_key_generator import generate_openai_style_api_key, generate_expiration_date

router = APIRouter()


@router.get("/providers", response_model=List[ProviderSchema])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Provider))
    providers = result.scalars().all()
    return providers


@router.get("/providers/{provider_id}", response_model=ProviderSchema)
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/providers", response_model=ProviderSchema)
async def create_provider(
    provider_data: ProviderCreate, db: AsyncSession = Depends(get_db)
):
    db_provider = Provider(**provider_data.model_dump())
    db.add(db_provider)
    await db.commit()
    await db.refresh(db_provider)
    return db_provider


@router.put("/providers/{provider_id}", response_model=ProviderSchema)
async def update_provider(
    provider_id: int, provider_data: ProviderUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = provider_data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(Provider).where(Provider.id == provider_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.commit()
    return {"detail": "Provider deleted successfully"}


@router.get("/api-keys", response_model=List[APIKeySchema])
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey))
    keys = result.scalars().all()
    return keys


@router.get("/api-keys/{key_id}", response_model=APIKeySchema)
async def get_api_key(key_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


@router.post("/api-keys", response_model=APIKeySchema)
async def create_api_key(key_data: APIKeyCreate, db: AsyncSession = Depends(get_db)):
    db_key = APIKey(**key_data.model_dump())
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    return db_key


@router.post("/api-keys/auto-generate", response_model=APIKeySchema)
async def auto_generate_api_key(key_data: APIKeyAutoCreate, db: AsyncSession = Depends(get_db)):
    """
    Auto-generate an API key in OpenAI/Anthropic style.
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
    key_id: int, key_data: APIKeyUpdate, db: AsyncSession = Depends(get_db)
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
async def delete_api_key(key_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(APIKey).where(APIKey.id == key_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.commit()
    return {"detail": "API key deleted successfully"}
