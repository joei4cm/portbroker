from typing import Any, Dict, List, Optional, Union

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.strategy import ModelStrategy, Provider, StrategyProviderMapping
from app.schemas.strategy import (
    ModelMappingRequest,
    ModelMappingResponse,
    ModelStrategyCreate,
    ModelStrategyUpdate,
    StrategyProviderMappingCreate,
    StrategyProviderMappingUpdate,
)


class StrategyService:
    """Service for managing model strategies and provider mappings"""

    @staticmethod
    async def create_strategy(
        db: AsyncSession, strategy_data: ModelStrategyCreate
    ) -> ModelStrategy:
        """Create a new model strategy with provider mappings"""
        # Extract base strategy data
        strategy_dict = strategy_data.model_dump(exclude={"provider_mappings"})
        db_strategy = ModelStrategy(**strategy_dict)
        db.add(db_strategy)

        # Flush to get the strategy ID
        await db.flush()

        # Create provider mappings if provided
        if strategy_data.provider_mappings:
            # Validate all providers exist before creating any mappings
            provider_ids = [mapping.provider_id for mapping in strategy_data.provider_mappings]
            
            # Check if all providers exist and are active
            existing_providers_result = await db.execute(
                select(Provider).where(
                    Provider.id.in_(provider_ids),
                    Provider.is_active == True
                )
            )
            existing_providers = {p.id: p for p in existing_providers_result.scalars().all()}
            
            # Validate each provider exists
            for mapping_data in strategy_data.provider_mappings:
                if mapping_data.provider_id not in existing_providers:
                    raise ValueError(f"Provider not found or inactive: {mapping_data.provider_id}")
            
            # Create mappings after validation
            for mapping_data in strategy_data.provider_mappings:
                mapping_dict = mapping_data.model_dump()
                mapping_dict["strategy_id"] = db_strategy.id
                db_mapping = StrategyProviderMapping(**mapping_dict)
                db.add(db_mapping)

        await db.commit()

        # Reload the strategy with all relationships loaded
        result = await db.execute(
            select(ModelStrategy)
            .where(ModelStrategy.id == db_strategy.id)
            .options(
                selectinload(ModelStrategy.provider_mappings).selectinload(
                    StrategyProviderMapping.provider
                )
            )
        )
        strategy_with_relationships = result.scalar_one()

        return strategy_with_relationships

    @staticmethod
    async def get_strategies(
        db: AsyncSession, strategy_type: Optional[str] = None
    ) -> List[ModelStrategy]:
        """Get all strategies with provider mappings, optionally filtered by type"""
        query = select(ModelStrategy).options(
            selectinload(ModelStrategy.provider_mappings).selectinload(
                StrategyProviderMapping.provider
            )
        )
        if strategy_type:
            query = query.where(ModelStrategy.strategy_type == strategy_type)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_strategy(
        db: AsyncSession, strategy_id: int
    ) -> Optional[ModelStrategy]:
        """Get a specific strategy by ID with provider mappings"""
        result = await db.execute(
            select(ModelStrategy)
            .where(ModelStrategy.id == strategy_id)
            .options(
                selectinload(ModelStrategy.provider_mappings).selectinload(
                    StrategyProviderMapping.provider
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_strategy(
        db: AsyncSession, strategy_id: int, strategy_data: ModelStrategyUpdate
    ) -> Optional[ModelStrategy]:
        """Update a strategy and its provider mappings"""
        # Get existing strategy with mappings
        result = await db.execute(
            select(ModelStrategy)
            .where(ModelStrategy.id == strategy_id)
            .options(selectinload(ModelStrategy.provider_mappings))
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            return None

        # Update base strategy fields
        update_data = strategy_data.model_dump(
            exclude={"provider_mappings"}, exclude_none=True
        )
        for field, value in update_data.items():
            setattr(strategy, field, value)

        # Update provider mappings if provided
        if strategy_data.provider_mappings is not None:
            # Remove existing mappings
            await db.execute(
                delete(StrategyProviderMapping).where(
                    StrategyProviderMapping.strategy_id == strategy_id
                )
            )

            # Add new mappings
            for mapping_data in strategy_data.provider_mappings:
                mapping_dict = mapping_data.model_dump()
                mapping_dict["strategy_id"] = strategy_id
                db_mapping = StrategyProviderMapping(**mapping_dict)
                db.add(db_mapping)

        await db.commit()

        # Reload the strategy with all relationships loaded
        result = await db.execute(
            select(ModelStrategy)
            .where(ModelStrategy.id == strategy_id)
            .options(
                selectinload(ModelStrategy.provider_mappings).selectinload(
                    StrategyProviderMapping.provider
                )
            )
        )
        strategy_with_relationships = result.scalar_one()

        return strategy_with_relationships

    @staticmethod
    async def delete_strategy(db: AsyncSession, strategy_id: int) -> bool:
        """Delete a strategy and its provider mappings"""
        # Delete provider mappings first (cascade will handle this, but being explicit)
        await db.execute(
            delete(StrategyProviderMapping).where(
                StrategyProviderMapping.strategy_id == strategy_id
            )
        )

        # Delete the strategy
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

        # Get strategies for the requested type with all relationships loaded
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
        """Map Anthropic model using tier-based fallback across multiple providers"""

        # Determine which tier to use
        preferred_tier = mapping_request.preferred_tier or "large"
        strategy_fallback_order = strategy.fallback_order
        fallback_order: List[str] = ["large", "medium", "small"]
        if strategy_fallback_order is not None:
            if isinstance(strategy_fallback_order, list):
                fallback_order = strategy_fallback_order

        # Get active provider mappings for this strategy, ordered by priority
        provider_mappings = sorted(
            [m for m in strategy.provider_mappings if m.is_active],
            key=lambda x: x.priority,
        )

        if not provider_mappings:
            raise ValueError(f"No active providers found for strategy: {strategy.name}")

        # Pre-fetch all provider data to avoid lazy loading issues
        provider_ids = [m.provider_id for m in provider_mappings]
        if provider_ids:
            providers_result = await db.execute(
                select(Provider).where(
                    Provider.id.in_(provider_ids), Provider.is_active == True
                )
            )
            active_providers = {p.id: p for p in providers_result.scalars().all()}
        else:
            active_providers = {}

        # First, try to find exact match across all providers and all tiers
        for mapping in provider_mappings:
            provider = active_providers.get(mapping.provider_id)
            if not provider:
                continue

            # Check all tiers for exact match
            for tier in ["large", "medium", "small"]:
                models = getattr(mapping, f"{tier}_models", [])
                for model in models:
                    if (
                        mapping_request.requested_model.lower() == model.lower()
                        and model in provider.model_list
                    ):
                        return ModelMappingResponse(
                            mapped_model=model,
                            provider_id=int(provider.id),
                            provider_name=str(provider.name),
                            tier_used=tier,
                            fallback_used=False,
                            available_models=models,
                        )

        # If no exact match found and fallback is enabled, try fallback logic
        if strategy.fallback_enabled:
            # Try each provider in priority order with preferred tier first
            for mapping in provider_mappings:
                provider = active_providers.get(mapping.provider_id)
                if not provider:
                    continue

                # Try each tier in fallback order
                for tier in fallback_order:
                    models = getattr(mapping, f"{tier}_models", [])
                    if models:
                        # Try to find any model from this tier that exists in the provider
                        provider_model_list = provider.model_list
                        provider_models: List[str] = []
                        if provider_model_list is not None:
                            if isinstance(provider_model_list, list):
                                provider_models = provider_model_list
                            else:
                                # Handle case where model_list might be a Column or other type
                                provider_models = []
                        for model in models:
                            if model in provider_models:
                                return ModelMappingResponse(
                                    mapped_model=model,
                                    provider_id=int(provider.id),
                                    provider_name=str(provider.name),
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
        """Map OpenAI model using selected models across multiple providers"""

        # Get active provider mappings for this strategy, ordered by priority
        provider_mappings = sorted(
            [m for m in strategy.provider_mappings if m.is_active],
            key=lambda x: x.priority,
        )

        if not provider_mappings:
            raise ValueError(f"No active providers found for strategy: {strategy.name}")

        # Pre-fetch all provider data to avoid lazy loading issues
        provider_ids = [m.provider_id for m in provider_mappings]
        if provider_ids:
            providers_result = await db.execute(
                select(Provider).where(
                    Provider.id.in_(provider_ids), Provider.is_active == True
                )
            )
            active_providers = {p.id: p for p in providers_result.scalars().all()}
        else:
            active_providers = {}

        # Try each provider in priority order
        for mapping in provider_mappings:
            provider = active_providers.get(mapping.provider_id)
            if not provider:
                continue

            # OpenAI strategies use selected_models
            selected_models = mapping.selected_models or []

            for selected_model in selected_models:
                # Check if the requested model matches the selected model and exists in provider
                if (
                    mapping_request.requested_model.lower() == selected_model.lower()
                    and selected_model in provider.model_list
                ):
                    return ModelMappingResponse(
                        mapped_model=selected_model,
                        provider_id=int(provider.id),
                        provider_name=str(provider.name),
                        tier_used="openai",
                        fallback_used=False,
                        available_models=selected_models,
                    )

        # If fallback is enabled and no exact match, try any selected model
        if strategy.fallback_enabled:
            for mapping in provider_mappings:
                provider = active_providers.get(mapping.provider_id)
                if not provider:
                    continue

                selected_models = mapping.selected_models or []
                for selected_model in selected_models:
                    if selected_model in provider.model_list:
                        return ModelMappingResponse(
                            mapped_model=selected_model,
                            provider_id=int(provider.id),
                            provider_name=str(provider.name),
                            tier_used="openai",
                            fallback_used=True,
                            available_models=selected_models,
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
        # Get all strategies with their provider mappings
        result = await db.execute(
            select(ModelStrategy)
            .where(ModelStrategy.is_active == True)
            .options(
                selectinload(ModelStrategy.provider_mappings).selectinload(
                    StrategyProviderMapping.provider
                )
            )
        )

        strategies_with_providers = []
        strategies = result.scalars().all()

        # Build the response
        for strategy in strategies:
            provider_mappings = []
            for mapping in strategy.provider_mappings:
                # Check if provider exists and is active
                if (
                    mapping.provider
                    and mapping.provider.is_active
                    and mapping.is_active
                ):
                    provider_info = {
                        "id": mapping.provider.id,
                        "name": mapping.provider.name,
                        "provider_type": mapping.provider.provider_type,
                        "model_list": mapping.provider.model_list,
                        "small_model": mapping.provider.small_model,
                        "medium_model": mapping.provider.medium_model,
                        "big_model": mapping.provider.big_model,
                        "priority": mapping.priority,
                        "mapping_id": mapping.id,
                        "large_models": mapping.large_models,
                        "medium_models": mapping.medium_models,
                        "small_models": mapping.small_models,
                        "selected_models": mapping.selected_models,
                    }
                    provider_mappings.append(provider_info)

            strategy_data = {
                "id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
                "strategy_type": strategy.strategy_type,
                "fallback_enabled": strategy.fallback_enabled,
                "fallback_order": strategy.fallback_order,
                "is_active": strategy.is_active,
                "provider_mappings": provider_mappings,
            }
            strategies_with_providers.append(strategy_data)

        return strategies_with_providers

    @staticmethod
    async def get_available_models_by_strategy_type(
        db: AsyncSession, strategy_type: str
    ) -> Dict[str, Any]:
        """Get available models for a specific strategy type from all providers"""
        # Validate strategy type
        if strategy_type not in ["anthropic", "openai"]:
            raise ValueError(f"Invalid strategy type: {strategy_type}")

        # Get all active providers
        result = await db.execute(select(Provider).where(Provider.is_active == True))
        providers = result.scalars().all()

        if not providers:
            return {"models": [], "providers": []}

        # Collect all models from all providers
        all_models = []
        provider_model_infos = []

        for provider in providers:
            provider_model_info: Dict[str, Any] = {
                "id": provider.id,
                "name": provider.name,
                "models": [],
            }

            provider_model_list = provider.model_list
            provider_models: List[str] = []
            if provider_model_list is not None:
                if isinstance(provider_model_list, list):
                    provider_models = provider_model_list
                else:
                    # Handle case where model_list might be a Column or other type
                    provider_models = []
            for model in provider_models:
                model_info = {
                    "id": str(model),
                    "name": str(model),
                    "provider_id": int(provider.id),
                    "provider_name": str(provider.name),
                }
                all_models.append(model_info)
                provider_model_info["models"].append(model_info)

            provider_model_infos.append(provider_model_info)

        return {"models": all_models, "providers": provider_model_infos}

    @staticmethod
    async def get_available_models_for_strategy(
        db: AsyncSession, provider_id: int
    ) -> Dict[str, Any]:
        """Get available models from a specific provider for strategy creation"""

        # Get the provider
        result = await db.execute(
            select(Provider).where(
                Provider.id == provider_id,
                Provider.is_active == True,
            )
        )
        provider = result.scalar_one_or_none()

        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        # Collect all models with provider info
        all_models = []

        provider_model_list = provider.model_list
        provider_models: List[str] = []
        if provider_model_list is not None:
            if isinstance(provider_model_list, list):
                provider_models = provider_model_list
            else:
                # Handle case where model_list might be a Column or other type
                provider_models = []
        for model in provider_models:
            all_models.append(
                {
                    "display_name": f"{provider.name} - {model}",
                    "model_name": str(model),
                    "provider_id": int(provider.id),
                    "provider_name": str(provider.name),
                }
            )

        # Sort by model name for consistent ordering
        all_models.sort(key=lambda x: str(x["model_name"]))

        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "provider_type": provider.provider_type,
            "models": all_models,
            "total_count": len(all_models),
        }

    @staticmethod
    async def add_provider_to_strategy(
        db: AsyncSession, strategy_id: int, mapping_data: StrategyProviderMappingCreate
    ) -> StrategyProviderMapping:
        """Add a provider mapping to an existing strategy"""

        # Verify strategy exists
        strategy_result = await db.execute(
            select(ModelStrategy).where(ModelStrategy.id == strategy_id)
        )
        strategy = strategy_result.scalar_one_or_none()
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        # Verify provider exists and is active
        provider_result = await db.execute(
            select(Provider).where(
                Provider.id == mapping_data.provider_id,
                Provider.is_active == True
            )
        )
        provider = provider_result.scalar_one_or_none()
        if not provider:
            raise ValueError(f"Provider not found or inactive: {mapping_data.provider_id}")

        # Check if mapping already exists
        existing_result = await db.execute(
            select(StrategyProviderMapping).where(
                StrategyProviderMapping.strategy_id == strategy_id,
                StrategyProviderMapping.provider_id == mapping_data.provider_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            raise ValueError(
                f"Provider already mapped to strategy: {mapping_data.provider_id}"
            )

        # Create mapping
        mapping_dict = mapping_data.model_dump()
        mapping_dict["strategy_id"] = strategy_id
        db_mapping = StrategyProviderMapping(**mapping_dict)
        db.add(db_mapping)
        await db.commit()
        await db.refresh(db_mapping)

        return db_mapping

    @staticmethod
    async def remove_provider_from_strategy(
        db: AsyncSession, strategy_id: int, provider_id: int
    ) -> bool:
        """Remove a provider mapping from a strategy"""
        result = await db.execute(
            delete(StrategyProviderMapping).where(
                StrategyProviderMapping.strategy_id == strategy_id,
                StrategyProviderMapping.provider_id == provider_id,
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def update_provider_mapping(
        db: AsyncSession, mapping_id: int, mapping_data: StrategyProviderMappingUpdate
    ) -> Optional[StrategyProviderMapping]:
        """Update a provider mapping"""
        # Get existing mapping
        result = await db.execute(
            select(StrategyProviderMapping).where(
                StrategyProviderMapping.id == mapping_id
            )
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            return None

        # Update fields
        update_data = mapping_data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(mapping, field, value)

        await db.commit()
        await db.refresh(mapping)
        return mapping
