from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ModelStrategy(Base):
    """Model strategy configuration for Anthropic and OpenAI model mapping"""

    __tablename__ = "model_strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Strategy type: 'anthropic' or 'openai'
    strategy_type = Column(String(20), nullable=False)

    # Model mappings for different tiers
    high_tier_models = Column(JSON, nullable=False, default=list)  # Primary models
    medium_tier_models = Column(JSON, nullable=False, default=list)  # Secondary models
    low_tier_models = Column(JSON, nullable=False, default=list)  # Fallback models

    # Fallback configuration
    fallback_enabled = Column(Boolean, nullable=False, default=True)
    fallback_order = Column(JSON, nullable=False, default=["high", "medium", "low"])

    # Provider selection
    provider_priority = Column(
        JSON, nullable=False, default=list
    )  # List of provider IDs in priority order

    # Metadata
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Note: Provider relationship removed - now strategies reference providers via provider_priority


class Provider(Base):
    """Provider model with strategy relationship"""

    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    provider_type = Column(String(50), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=False)

    # Model configuration
    model_list = Column(JSON, nullable=False, default=list)
    small_model = Column(String(100), nullable=True)
    medium_model = Column(String(100), nullable=True)
    big_model = Column(String(100), nullable=True)

    # Additional configuration
    headers = Column(JSON, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    temperature_default = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Note: Strategy relationship removed - now strategies reference providers

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class APIKey(Base):
    """API key model"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_name = Column(String(100), nullable=False)
    api_key = Column(String(500), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
