from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import ModelStrategy, Provider
from app.schemas.strategy import (
    ModelMappingRequest,
    ModelMappingResponse,
    ModelStrategyCreate,
    ModelStrategyUpdate,
)


class StrategyService:
    """Service for managing model strategies and provider mappings"""

    @staticmethod
    async def create_strategy(
        db: AsyncSession, strategy_data: ModelStrategyCreate
    ) -> ModelStrategy:
        """Create a new model strategy"""
        db_strategy = ModelStrategy(**strategy_data.model_dump())
        db.add(db_strategy)
        await db.commit()
        await db.refresh(db_strategy)
        return db_strategy

    @staticmethod
    async def get_strategies(
        db: AsyncSession, strategy_type: Optional[str] = None
    ) -> List[ModelStrategy]:
        """Get all strategies, optionally filtered by type"""
        query = select(ModelStrategy)
        if strategy_type:
            query = query.where(ModelStrategy.strategy_type == strategy_type)
        query = query.where(ModelStrategy.is_active == True)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_strategy(
        db: AsyncSession, strategy_id: int
    ) -> Optional[ModelStrategy]:
        """Get a specific strategy by ID"""
        result = await db.execute(
            select(ModelStrategy).where(ModelStrategy.id == strategy_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_strategy(
        db: AsyncSession, strategy_id: int, strategy_data: ModelStrategyUpdate
    ) -> Optional[ModelStrategy]:
        """Update a strategy"""
        # Get existing strategy
        result = await db.execute(
            select(ModelStrategy).where(ModelStrategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            return None

        # Update fields
        update_data = strategy_data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(strategy, field, value)

        await db.commit()
        await db.refresh(strategy)
        return strategy

    @staticmethod
    async def delete_strategy(db: AsyncSession, strategy_id: int) -> bool:
        """Delete a strategy"""
        result = await db.execute(
            delete(ModelStrategy).where(ModelStrategy.id == strategy_id)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def map_model(
        db: AsyncSession, mapping_request: ModelMappingRequest
    ) -> ModelMappingResponse:
        """Map a requested model to an available provider model using strategy"""

        # Get strategies for the requested type
        strategies = await StrategyService.get_strategies(
            db, mapping_request.strategy_type
        )
        if not strategies:
            raise ValueError(
                f"No strategies found for type: {mapping_request.strategy_type}"
            )

        # Use the first active strategy (could be enhanced to select by priority)
        strategy = strategies[0]

        if mapping_request.strategy_type == "anthropic":
            return await StrategyService._map_anthropic_model(
                db, strategy, mapping_request
            )
        elif mapping_request.strategy_type == "openai":
            return await StrategyService._map_openai_model(
                db, strategy, mapping_request
            )
        else:
            raise ValueError(
                f"Unsupported strategy type: {mapping_request.strategy_type}"
            )

    @staticmethod
    async def _map_anthropic_model(
        db: AsyncSession, strategy: ModelStrategy, mapping_request: ModelMappingRequest
    ) -> ModelMappingResponse:
        """Map Anthropic model using tier-based fallback"""

        # Determine which tier to use
        preferred_tier = mapping_request.preferred_tier or "high"
        fallback_order = strategy.fallback_order or ["high", "medium", "low"]

        # Try each tier in fallback order
        for tier in fallback_order:
            if preferred_tier == tier or not mapping_request.preferred_tier:
                models = getattr(strategy, f"{tier}_tier_models", [])

                # Find exact matching model
                for model in models:
                    if mapping_request.requested_model.lower() == model.lower():
                        # Find a provider that has this model using the strategy's provider priority
                        provider = await StrategyService._find_provider_for_model(
                            db, model, strategy.provider_priority
                        )

                        if provider:
                            return ModelMappingResponse(
                                mapped_model=model,
                                provider_id=provider.id,
                                provider_name=provider.name,
                                tier_used=tier,
                                fallback_used=tier != preferred_tier,
                                available_models=models,
                            )

        # If no exact match found, try to find any available model with fallback
        if strategy.fallback_enabled:
            for tier in fallback_order:
                models = getattr(strategy, f"{tier}_tier_models", [])
                if models:
                    # Try to find any provider that has any model from this tier
                    for model in models:
                        provider = await StrategyService._find_provider_for_model(
                            db, model, strategy.provider_priority
                        )
                        if provider:
                            return ModelMappingResponse(
                                mapped_model=model,
                                provider_id=provider.id,
                                provider_name=provider.name,
                                tier_used=tier,
                                fallback_used=True,
                                available_models=models,
                            )

        raise ValueError(
            f"No suitable model found for: {mapping_request.requested_model}"
        )

    @staticmethod
    async def _map_openai_model(
        db: AsyncSession, strategy: ModelStrategy, mapping_request: ModelMappingRequest
    ) -> ModelMappingResponse:
        """Map OpenAI model using single model selection"""

        # OpenAI strategies use high_tier_models as the selected model (single model)
        selected_model = None
        model_list = strategy.high_tier_models or []

        if model_list:
            selected_model = model_list[0]  # Use the first (and only) model

        if not selected_model:
            raise ValueError("No model configured for OpenAI strategy")

        # Check if the requested model matches the selected model
        if mapping_request.requested_model.lower() == selected_model.lower():
            # Find a provider that has this model using the strategy's provider priority
            provider = await StrategyService._find_provider_for_model(
                db, selected_model, strategy.provider_priority
            )

            if provider:
                return ModelMappingResponse(
                    mapped_model=selected_model,
                    provider_id=provider.id,
                    provider_name=provider.name,
                    tier_used="openai",
                    fallback_used=False,
                    available_models=[selected_model],
                )

        # If fallback is enabled and no exact match, try the selected model anyway
        if strategy.fallback_enabled:
            provider = await StrategyService._find_provider_for_model(
                db, selected_model, strategy.provider_priority
            )
            if provider:
                return ModelMappingResponse(
                    mapped_model=selected_model,
                    provider_id=provider.id,
                    provider_name=provider.name,
                    tier_used="openai",
                    fallback_used=True,
                    available_models=[selected_model],
                )

        raise ValueError(
            f"No suitable model found for: {mapping_request.requested_model}"
        )

    @staticmethod
    async def _find_provider_for_model(
        db: AsyncSession, model: str, provider_priority: List[int]
    ) -> Optional[Provider]:
        """Find a provider that has the specified model"""

        # If priority list is provided, try providers in that order
        if provider_priority:
            for provider_id in provider_priority:
                result = await db.execute(
                    select(Provider).where(
                        Provider.id == provider_id,
                        Provider.is_active == True,
                    )
                )
                provider = result.scalar_one_or_none()
                if provider and model in provider.model_list:
                    return provider

        # Otherwise, find any active provider with the model
        result = await db.execute(select(Provider).where(Provider.is_active == True))
        providers = result.scalars().all()
        for provider in providers:
            if model in provider.model_list:
                return provider

        return None

    @staticmethod
    async def get_providers_with_strategies(db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all providers with their strategy information"""
        result = await db.execute(select(Provider).where(Provider.is_active == True))

        providers_with_strategies = []
        for provider in result:
            provider_data = {
                "id": provider.id,
                "name": provider.name,
                "provider_type": provider.provider_type,
                "base_url": provider.base_url,
                "model_list": provider.model_list,
                "small_model": provider.small_model,
                "medium_model": provider.medium_model,
                "big_model": provider.big_model,
                "is_active": provider.is_active,
                "strategy_id": None,  # No longer used
                "strategy_name": None,  # No longer used
            }
            providers_with_strategies.append(provider_data)

        return providers_with_strategies

    @staticmethod
    async def get_strategies_with_providers(db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all strategies with their provider information"""
        result = await db.execute(
            select(ModelStrategy).where(ModelStrategy.is_active == True)
        )

        strategies_with_providers = []
        for strategy in result.scalars().all():
            # Get all providers referenced in the strategy's provider priority
            providers = []
            if strategy.provider_priority:
                for provider_id in strategy.provider_priority:
                    provider_result = await db.execute(
                        select(Provider).where(
                            Provider.id == provider_id, Provider.is_active == True
                        )
                    )
                    provider = provider_result.scalar_one_or_none()
                    if provider:
                        providers.append(
                            {
                                "id": provider.id,
                                "name": provider.name,
                                "provider_type": provider.provider_type,
                                "model_list": provider.model_list,
                                "small_model": provider.small_model,
                                "medium_model": provider.medium_model,
                                "big_model": provider.big_model,
                            }
                        )

            strategy_data = {
                "id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
                "strategy_type": strategy.strategy_type,
                "high_tier_models": strategy.high_tier_models,
                "medium_tier_models": strategy.medium_tier_models,
                "low_tier_models": strategy.low_tier_models,
                "fallback_enabled": strategy.fallback_enabled,
                "fallback_order": strategy.fallback_order,
                "provider_priority": strategy.provider_priority,
                "is_active": strategy.is_active,
                "providers": providers,
            }
            strategies_with_providers.append(strategy_data)

        return strategies_with_providers

    @staticmethod
    async def get_available_models_for_strategy(
        db: AsyncSession, strategy_type: str
    ) -> Dict[str, Any]:
        """Get available models from all providers for strategy creation"""

        if strategy_type not in ["anthropic", "openai"]:
            raise ValueError(f"Invalid strategy type: {strategy_type}")

        # Get all active providers
        result = await db.execute(select(Provider).where(Provider.is_active == True))
        providers = result.scalars().all()

        # Collect all models with provider info
        all_models = []

        for provider in providers:
            if provider.model_list:
                for model in provider.model_list:
                    # For OpenAI strategies, include all models
                    # For Anthropic strategies, filter to Claude models
                    if strategy_type == "openai" or "claude" in model.lower():
                        all_models.append(
                            {
                                "display_name": f"{provider.name} - {model}",
                                "model_name": model,
                                "provider_id": provider.id,
                                "provider_name": provider.name,
                            }
                        )

        # Sort by provider name and model name for consistent ordering
        all_models.sort(key=lambda x: (x["provider_name"], x["model_name"]))

        return {
            "strategy_type": strategy_type,
            "models": all_models,
            "total_count": len(all_models),
        }
