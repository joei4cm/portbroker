from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin_user, get_current_portal_user
from app.core.database import get_db
from app.models.strategy import Provider
from app.schemas.strategy import (
    ModelMappingRequest,
    ModelMappingResponse,
    ModelStrategy,
    ModelStrategyCreate,
    ModelStrategyUpdate,
    StrategyProviderMappingCreate,
    StrategyProviderMappingUpdate,
)
from app.services.strategy_service import StrategyService

router = APIRouter()


@router.options("/strategies")
async def options_strategies(request: Request):
    """Handle CORS preflight requests for strategies endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategies/{strategy_id}")
async def options_strategy_by_id(request: Request):
    """Handle CORS preflight requests for strategy by ID endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/providers-with-strategies")
async def options_providers_with_strategies(request: Request):
    """Handle CORS preflight requests for providers with strategies endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategies-with-providers")
async def options_strategies_with_providers(request: Request):
    """Handle CORS preflight requests for strategies with providers endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategy-models")
async def options_strategy_models(request: Request):
    """Handle CORS preflight requests for strategy models endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/providers-dropdown")
async def options_providers_dropdown(request: Request):
    """Handle CORS preflight requests for providers dropdown endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/map-model")
async def options_map_model(request: Request):
    """Handle CORS preflight requests for map model endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategies/{strategy_id}/activate")
async def options_activate_strategy(request: Request):
    """Handle CORS preflight requests for activate strategy endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategies/{strategy_id}/deactivate")
async def options_deactivate_strategy(request: Request):
    """Handle CORS preflight requests for deactivate strategy endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategies/{strategy_id}/providers")
async def options_strategy_providers(request: Request):
    """Handle CORS preflight requests for strategy providers endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategies/{strategy_id}/providers/{provider_id}")
async def options_strategy_provider_by_id(request: Request):
    """Handle CORS preflight requests for strategy provider by ID endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@router.options("/strategies/{strategy_id}/providers/{mapping_id}")
async def options_provider_mapping(request: Request):
    """Handle CORS preflight requests for provider mapping endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "PUT, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


def convert_old_strategy_to_new(old_data: dict) -> ModelStrategyCreate:
    """Convert old strategy format to new format with provider mappings"""
    provider_id = old_data.pop("provider_id", None)

    # Create provider mapping if provider_id is provided
    provider_mappings = []
    if provider_id:
        if old_data.get("strategy_type") == "anthropic":
            mapping = StrategyProviderMappingCreate(
                provider_id=provider_id,
                large_models=old_data.get("large_models", []),
                medium_models=old_data.get("medium_models", []),
                small_models=old_data.get("small_models", []),
                selected_models=[],
                priority=1,
                is_active=True,
            )
        else:  # openai
            mapping = StrategyProviderMappingCreate(
                provider_id=provider_id,
                large_models=[],
                medium_models=[],
                small_models=[],
                selected_models=old_data.get(
                    "large_models", []
                ),  # OpenAI uses selected_models
                priority=1,
                is_active=True,
            )
        provider_mappings.append(mapping)

    # Remove old model fields from strategy data
    for field in ["large_models", "medium_models", "small_models"]:
        old_data.pop(field, None)

    # Create new strategy with provider mappings
    return ModelStrategyCreate(**old_data, provider_mappings=provider_mappings)


@router.get("/strategies")
async def get_strategies(
    strategy_type: Optional[str] = Query(
        None, description="Filter by strategy type (anthropic or openai)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all model strategies"""
    return await StrategyService.get_strategies(db, strategy_type)


@router.get("/strategies/{strategy_id}")
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get a specific strategy"""
    strategy = await StrategyService.get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.post("/strategies")
async def create_strategy(
    strategy_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Create a new model strategy"""
    # Check if this is old format (has provider_id field)
    if "provider_id" in strategy_data:
        # Convert old format to new format
        strategy_data_copy = strategy_data.copy()
        new_strategy_data = convert_old_strategy_to_new(strategy_data_copy)
        return await StrategyService.create_strategy(db, new_strategy_data)
    else:
        # Already in new format
        new_strategy_data = ModelStrategyCreate(**strategy_data)
        return await StrategyService.create_strategy(db, new_strategy_data)


@router.put("/strategies/{strategy_id}", response_model=ModelStrategy)
async def update_strategy(
    strategy_id: int,
    strategy_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Update a model strategy"""
    # Check if this is old format (has provider_id field)
    if "provider_id" in strategy_data:
        # Convert old format to new format
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
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Delete a model strategy"""
    success = await StrategyService.delete_strategy(db, strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"detail": "Strategy deleted successfully"}


@router.post("/map-model", response_model=ModelMappingResponse)
async def map_model(
    mapping_request: ModelMappingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Map a requested model to an available provider model"""
    try:
        return await StrategyService.map_model(db, mapping_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers-with-strategies")
async def get_providers_with_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all providers with their strategy information"""
    return await StrategyService.get_providers_with_strategies(db)


@router.get("/strategies-with-providers")
async def get_strategies_with_providers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all strategies with their provider information"""
    return await StrategyService.get_strategies_with_providers(db)


@router.get("/strategy-models")
async def get_available_models(
    strategy_type: str = Query(..., description="Strategy type (anthropic or openai)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get available models for a specific strategy type from all providers"""
    try:
        return await StrategyService.get_available_models_by_strategy_type(
            db, strategy_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/strategies/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Activate a strategy (deactivates other strategies of the same type)"""
    try:
        strategy = await StrategyService.activate_strategy(db, strategy_id)
        return strategy
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/strategies/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Deactivate a strategy"""
    try:
        strategy = await StrategyService.deactivate_strategy(db, strategy_id)
        return strategy
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/providers-dropdown")
async def get_providers_dropdown(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all active providers for dropdown selection"""
    result = await db.execute(select(Provider).where(Provider.is_active == True))
    providers = result.scalars().all()

    dropdown_options = []
    for provider in providers:
        dropdown_options.append(
            {
                "id": provider.id,
                "name": provider.name,
                "provider_type": provider.provider_type,
                "model_count": len(provider.model_list) if provider.model_list else 0,
            }
        )

    return {"providers": dropdown_options, "total_count": len(dropdown_options)}


@router.post("/strategies/{strategy_id}/providers")
async def add_provider_to_strategy(
    strategy_id: int,
    mapping_data: StrategyProviderMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Add a provider to an existing strategy"""
    try:
        mapping = await StrategyService.add_provider_to_strategy(
            db, strategy_id, mapping_data
        )
        return mapping
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/strategies/{strategy_id}/providers/{provider_id}")
async def remove_provider_from_strategy(
    strategy_id: int,
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Remove a provider from a strategy"""
    success = await StrategyService.remove_provider_from_strategy(
        db, strategy_id, provider_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Provider mapping not found")
    return {"detail": "Provider removed from strategy successfully"}


@router.put("/strategies/{strategy_id}/providers/{mapping_id}")
async def update_provider_mapping(
    strategy_id: int,
    mapping_id: int,
    mapping_data: StrategyProviderMappingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Update a provider mapping within a strategy"""
    mapping = await StrategyService.update_provider_mapping(
        db, mapping_id, mapping_data
    )
    if not mapping:
        raise HTTPException(status_code=404, detail="Provider mapping not found")
    return mapping
