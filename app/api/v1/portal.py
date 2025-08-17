from typing import Dict, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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


def parse_datetime_string(dt_string: str) -> datetime:
    """Parse datetime string in ISO format to datetime object"""
    try:
        # Try to parse ISO format datetime string
        if dt_string.endswith('Z'):
            # Handle UTC timezone
            dt_string = dt_string[:-1] + '+00:00'
        return datetime.fromisoformat(dt_string)
    except (ValueError, TypeError):
        # If parsing fails, return None
        return None


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

    # Update other fields (exclude datetime fields and auto-generated fields)
    excluded_fields = {"id", "created_at", "updated_at", "api_key"}
    for field, value in key_data.items():
        if field != "regenerate" and value is not None and field not in excluded_fields:
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
    
    # Handle datetime fields specifically
    if "created_at" in provider_data and provider_data["created_at"] is not None:
        if isinstance(provider_data["created_at"], str):
            parsed_dt = parse_datetime_string(provider_data["created_at"])
            if parsed_dt:
                provider.created_at = parsed_dt
    
    # Update fields manually (exclude auto-generated fields)
    # Only update fields that are present in the request data
    update_fields = [
        "name", "provider_type", "base_url", "api_key", "model_list",
        "small_model", "medium_model", "big_model", "headers", 
        "max_tokens", "temperature_default", "verify_ssl", "is_active"
    ]
    
    for field in update_fields:
        if field in provider_data:
            # Only update if the value is not None or if it's a boolean/number that can be None
            if provider_data[field] is not None or isinstance(provider_data[field], (bool, int, float)):
                setattr(provider, field, provider_data[field])

    await db.commit()
    await db.refresh(provider)
    return provider


# Statistics endpoints
@router.get("/statistics/dashboard")
async def get_dashboard_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get dashboard statistics"""
    from app.services.statistics_service import StatisticsService
    return await StatisticsService.get_dashboard_stats(db)


@router.get("/statistics/providers")
async def get_provider_statistics(
    days: int = Query(7, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get provider usage statistics"""
    from app.services.statistics_service import StatisticsService
    return await StatisticsService.get_provider_stats(db, days)


@router.get("/statistics/strategies")
async def get_strategy_statistics(
    days: int = Query(7, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get strategy usage statistics"""
    from app.services.statistics_service import StatisticsService
    return await StatisticsService.get_strategy_stats(db, days)


@router.get("/statistics/activity")
async def get_recent_activity(
    limit: int = Query(10, description="Number of recent activities to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get recent activity for dashboard"""
    from app.services.statistics_service import StatisticsService
    return await StatisticsService.get_recent_activity(db, limit)


@router.get("/statistics/hourly")
async def get_hourly_statistics(
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get hourly request statistics"""
    from app.services.statistics_service import StatisticsService
    return await StatisticsService.get_hourly_request_counts(db, hours)


# Strategy endpoints for portal compatibility
@router.get("/strategy-models")
async def get_strategy_models(
    strategy_type: str = Query(..., description="Strategy type (anthropic or openai)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get available models for a specific strategy type from all providers"""
    from app.services.strategy_service import StrategyService
    try:
        return await StrategyService.get_available_models_by_strategy_type(db, strategy_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/strategies")
async def get_portal_strategies(
    strategy_type: str = Query(None, description="Filter by strategy type (anthropic or openai)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all model strategies for portal"""
    from app.services.strategy_service import StrategyService
    return await StrategyService.get_strategies(db, strategy_type)


@router.post("/strategies")
async def create_portal_strategy(
    strategy_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Create a new model strategy for portal"""
    from app.services.strategy_service import StrategyService
    from app.schemas.strategy import ModelStrategyCreate
    
    # Check if this is old format (has provider_id field)
    if "provider_id" in strategy_data:
        # Convert old format to new format
        from app.api.v1.strategies import convert_old_strategy_to_new
        strategy_data_copy = strategy_data.copy()
        new_strategy_data = convert_old_strategy_to_new(strategy_data_copy)
        return await StrategyService.create_strategy(db, new_strategy_data)
    else:
        # Already in new format
        new_strategy_data = ModelStrategyCreate(**strategy_data)
        return await StrategyService.create_strategy(db, new_strategy_data)


@router.put("/strategies/{strategy_id}")
async def update_portal_strategy(
    strategy_id: int,
    strategy_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Update a model strategy for portal"""
    from app.services.strategy_service import StrategyService
    from app.schemas.strategy import ModelStrategyUpdate
    
    # Check if this is old format (has provider_id field)
    if "provider_id" in strategy_data:
        # Convert old format to new format
        from app.api.v1.strategies import convert_old_strategy_to_new
        strategy_data_copy = strategy_data.copy()
        new_strategy_data = convert_old_strategy_to_new(strategy_data_copy)
        # Convert to update format
        update_data = ModelStrategyUpdate(**new_strategy_data.model_dump())
    else:
        # Already in new format
        update_data = ModelStrategyUpdate(**strategy_data)

    strategy = await StrategyService.update_strategy(db, strategy_id, update_data)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.delete("/strategies/{strategy_id}")
async def delete_portal_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Delete a model strategy for portal"""
    from app.services.strategy_service import StrategyService
    success = await StrategyService.delete_strategy(db, strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"detail": "Strategy deleted successfully"}


@router.post("/strategies/{strategy_id}/activate")
async def activate_portal_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Activate a strategy for portal"""
    from app.services.strategy_service import StrategyService
    try:
        strategy = await StrategyService.activate_strategy(db, strategy_id)
        return strategy
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/strategies/{strategy_id}/deactivate")
async def deactivate_portal_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Deactivate a strategy for portal"""
    from app.services.strategy_service import StrategyService
    try:
        strategy = await StrategyService.deactivate_strategy(db, strategy_id)
        return strategy
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
