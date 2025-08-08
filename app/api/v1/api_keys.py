from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    get_current_admin_user,
    get_current_api_key,
    get_current_admin_api_key,
    get_optional_api_key,
)
from app.core.database import get_db
from app.models.strategy import APIKey
from app.schemas.provider import APIKey as APIKeySchema
from app.schemas.provider import (
    APIKeyAutoCreate,
    APIKeyUpdate,
)
from app.utils.api_key_generator import (
    generate_expiration_date,
    generate_openai_style_api_key,
)

router = APIRouter()


@router.get("/api-keys", response_model=List[APIKeySchema])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_api_key),
):
    """List all API keys (accessible by authenticated users)"""
    result = await db.execute(select(APIKey))
    keys = result.scalars().all()
    return keys


@router.get("/api-keys/public", response_model=List[APIKeySchema])
async def list_api_keys_public(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_optional_api_key),
):
    """List all API keys (accessible by anyone, but limited data)"""
    result = await db.execute(select(APIKey))
    keys = result.scalars().all()
    # Return limited data for unauthenticated users
    if not current_user:
        return [
            {"id": key.id, "key_name": key.key_name, "is_active": key.is_active}
            for key in keys
        ]
    return keys


@router.get("/api-keys/{key_id}", response_model=APIKeySchema)
async def get_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_api_key),
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
    current_user: dict = Depends(get_current_admin_api_key),
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
    key_data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_api_key),
):
    """Update an existing API key (admin only)"""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    update_data = key_data.model_dump(exclude_none=True)

    # Handle key regeneration
    if update_data.get("regenerate"):
        # Generate a new API key
        api_key.api_key = generate_openai_style_api_key()
        # Remove regenerate from update_data as it's not a model field
        update_data.pop("regenerate", None)

    # Update other fields
    for field, value in update_data.items():
        setattr(api_key, field, value)

    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_api_key),
):
    """Delete an API key (admin only)"""
    result = await db.execute(delete(APIKey).where(APIKey.id == key_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.commit()
    return {"detail": "API key deleted successfully"}


@router.post("/api-keys/with-expiry")
async def create_api_key_with_expiry(
    key_name: str,
    api_key: str,
    description: Optional[str] = None,
    expires_in_days: Optional[int] = None,
    is_admin: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_api_key),
):
    """Create API key with optional expiration (admin only)"""
    expires_at = None
    if expires_in_days and expires_in_days > 0:
        expires_at = datetime.now() + timedelta(days=expires_in_days)

    db_key = APIKey(
        key_name=key_name,
        api_key=api_key,
        description=description,
        is_admin=is_admin,
        expires_at=expires_at,
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    return db_key
