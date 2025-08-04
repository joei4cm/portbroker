from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin_api_key, get_current_api_key
from app.core.database import get_db
from app.models.strategy import Provider
from app.schemas.provider import Provider as ProviderSchema
from app.schemas.provider import ProviderCreate, ProviderUpdate

router = APIRouter()


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


@router.get("/models")
async def get_all_models(
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_api_key),
):
    """Get all models from all active providers (authenticated users)"""
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
                    }
                )

    return {"models": all_models}
