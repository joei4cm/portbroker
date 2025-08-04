from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin_user, get_current_portal_user
from app.core.database import get_db
from app.schemas.strategy import (
    ModelMappingRequest,
    ModelMappingResponse,
    ModelStrategy,
    ModelStrategyCreate,
    ModelStrategyUpdate,
)
from app.services.strategy_service import StrategyService

router = APIRouter()


@router.get("/strategies", response_model=List[ModelStrategy])
async def get_strategies(
    strategy_type: Optional[str] = Query(
        None, description="Filter by strategy type (anthropic or openai)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_portal_user),
):
    """Get all model strategies"""
    return await StrategyService.get_strategies(db, strategy_type)


@router.get("/strategies/{strategy_id}", response_model=ModelStrategy)
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


@router.post("/strategies", response_model=ModelStrategy)
async def create_strategy(
    strategy_data: ModelStrategyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Create a new model strategy"""
    return await StrategyService.create_strategy(db, strategy_data)


@router.put("/strategies/{strategy_id}", response_model=ModelStrategy)
async def update_strategy(
    strategy_id: int,
    strategy_data: ModelStrategyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Update a model strategy"""
    strategy = await StrategyService.update_strategy(db, strategy_id, strategy_data)
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
    """Get available models from all providers, formatted as dropdown options"""
    try:
        return await StrategyService.get_available_models_for_strategy(
            db, strategy_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
