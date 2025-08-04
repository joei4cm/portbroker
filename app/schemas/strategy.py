from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelStrategyBase(BaseModel):
    """Base schema for ModelStrategy"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    strategy_type: str = Field(..., pattern="^(anthropic|openai)$")
    high_tier_models: List[str] = Field(default_factory=list)
    medium_tier_models: List[str] = Field(default_factory=list)
    low_tier_models: List[str] = Field(default_factory=list)
    fallback_enabled: bool = True
    fallback_order: List[str] = Field(default=["high", "medium", "low"])
    provider_priority: List[int] = Field(default_factory=list)
    is_active: bool = True


class ModelStrategyCreate(ModelStrategyBase):
    """Schema for creating ModelStrategy"""

    pass


class ModelStrategyUpdate(BaseModel):
    """Schema for updating ModelStrategy"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    strategy_type: Optional[str] = Field(None, pattern="^(anthropic|openai)$")
    high_tier_models: Optional[List[str]] = None
    medium_tier_models: Optional[List[str]] = None
    low_tier_models: Optional[List[str]] = None
    fallback_enabled: Optional[bool] = None
    fallback_order: Optional[List[str]] = None
    provider_priority: Optional[List[int]] = None
    is_active: Optional[bool] = None


class ModelStrategy(ModelStrategyBase):
    """Full ModelStrategy schema"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProviderStrategy(BaseModel):
    """Provider information (strategy relationship removed)"""

    id: int
    name: str
    provider_type: str
    base_url: str
    model_list: List[str]
    small_model: Optional[str]
    medium_model: Optional[str]
    big_model: Optional[str]
    is_active: bool


class ModelMappingRequest(BaseModel):
    """Request model for mapping models"""

    requested_model: str
    strategy_type: str = Field(..., pattern="^(anthropic|openai)$")
    preferred_tier: Optional[str] = Field(None, pattern="^(high|medium|low)$")


class ModelMappingResponse(BaseModel):
    """Response model for model mapping"""

    mapped_model: str
    provider_id: int
    provider_name: str
    tier_used: str
    fallback_used: bool = False
    available_models: List[str]
