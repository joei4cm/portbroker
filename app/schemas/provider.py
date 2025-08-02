from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderBase(BaseModel):
    name: str = Field(..., description="Provider name")
    provider_type: str = Field(
        ..., description="Type of provider (openai, azure, custom)"
    )
    base_url: str = Field(..., description="Base URL for the provider API")
    api_key: str = Field(..., description="API key for authentication")
    model_list: Optional[List[str]] = Field(
        None, description="List of available models"
    )
    big_model: Optional[str] = Field(
        None, description="Model for high-complexity requests"
    )
    small_model: Optional[str] = Field(
        None, description="Model for low-complexity requests"
    )
    medium_model: Optional[str] = Field(
        None, description="Model for medium-complexity requests"
    )
    is_active: bool = Field(True, description="Whether the provider is active")
    priority: int = Field(1, description="Provider priority (higher = preferred)")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens limit")
    temperature_default: Optional[str] = Field(None, description="Default temperature")
    headers: Optional[Dict[str, Any]] = Field(None, description="Additional headers")


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_list: Optional[List[str]] = None
    big_model: Optional[str] = None
    small_model: Optional[str] = None
    medium_model: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature_default: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None


class Provider(ProviderBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyBase(BaseModel):
    key_name: str = Field(..., description="Name/identifier for the API key")
    api_key: str = Field(..., description="The actual API key")
    description: Optional[str] = Field(None, description="Description of the key")
    is_active: bool = Field(True, description="Whether the key is active")
    expires_at: Optional[datetime] = Field(
        None, description="Expiration date for the API key"
    )


class APIKeyCreate(APIKeyBase):
    pass


class APIKeyUpdate(BaseModel):
    key_name: Optional[str] = None
    api_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class APIKey(APIKeyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
