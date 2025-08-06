from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyProviderMappingBase(BaseModel):
    """Base schema for StrategyProviderMapping"""

    provider_id: int = Field(..., gt=0)
    large_models: List[str] = Field(default_factory=list)
    medium_models: List[str] = Field(default_factory=list)
    small_models: List[str] = Field(default_factory=list)
    selected_models: List[str] = Field(default_factory=list)
    priority: int = Field(1, ge=1)
    is_active: bool = True


class StrategyProviderMappingCreate(StrategyProviderMappingBase):
    """Schema for creating StrategyProviderMapping"""

    pass


class StrategyProviderMappingUpdate(BaseModel):
    """Schema for updating StrategyProviderMapping"""

    provider_id: Optional[int] = Field(None, gt=0)
    large_models: Optional[List[str]] = None
    medium_models: Optional[List[str]] = None
    small_models: Optional[List[str]] = None
    selected_models: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class StrategyProviderMapping(StrategyProviderMappingBase):
    """Full StrategyProviderMapping schema"""

    id: int
    strategy_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModelStrategyBase(BaseModel):
    """Base schema for ModelStrategy"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    strategy_type: str = Field(..., pattern="^(anthropic|openai)$")
    fallback_enabled: bool = True
    fallback_order: List[str] = Field(default=["large", "medium", "small"])
    is_active: bool = True


class ModelStrategyCreate(ModelStrategyBase):
    """Schema for creating ModelStrategy"""

    provider_mappings: List[StrategyProviderMappingCreate] = Field(default_factory=list)


class ModelStrategyUpdate(BaseModel):
    """Schema for updating ModelStrategy"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    strategy_type: Optional[str] = Field(None, pattern="^(anthropic|openai)$")
    fallback_enabled: Optional[bool] = None
    fallback_order: Optional[List[str]] = None
    is_active: Optional[bool] = None
    provider_mappings: Optional[List[StrategyProviderMappingCreate]] = None


class ModelStrategy(ModelStrategyBase):
    """Full ModelStrategy schema"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    provider_mappings: List[StrategyProviderMapping] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ProviderInfo(BaseModel):
    """Provider information"""

    id: int
    name: str
    provider_type: str
    base_url: str
    model_list: List[str]
    small_model: Optional[str]
    medium_model: Optional[str]
    big_model: Optional[str]
    is_active: bool


class StrategyProviderMappingWithProvider(StrategyProviderMapping):
    """StrategyProviderMapping with provider information"""

    provider: ProviderInfo


class ModelStrategyWithProviders(ModelStrategyBase):
    """ModelStrategy with provider mappings and provider information"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    provider_mappings: List[StrategyProviderMappingWithProvider] = Field(
        default_factory=list
    )


class ModelMappingRequest(BaseModel):
    """Request model for mapping models"""

    requested_model: str
    strategy_type: str = Field(..., pattern="^(anthropic|openai)$")
    preferred_tier: Optional[str] = Field(None, pattern="^(large|medium|small)$")


class ModelMappingResponse(BaseModel):
    """Response model for model mapping"""

    mapped_model: str
    provider_id: int
    provider_name: str
    tier_used: str
    fallback_used: bool = False
    available_models: List[str]
