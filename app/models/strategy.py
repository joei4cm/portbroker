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

    # Fallback configuration
    fallback_enabled = Column(Boolean, nullable=False, default=True)
    fallback_order = Column(JSON, nullable=False, default=["large", "medium", "small"])

    # Metadata
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    provider_mappings = relationship(
        "StrategyProviderMapping",
        back_populates="strategy",
        cascade="all, delete-orphan",
    )


class StrategyProviderMapping(Base):
    """Mapping between strategy and provider with specific model configurations"""

    __tablename__ = "strategy_provider_mappings"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("model_strategies.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)

    # Model mappings for different tiers (for Anthropic strategies)
    large_models = Column(JSON, nullable=False, default=list)  # Large/primary models
    medium_models = Column(
        JSON, nullable=False, default=list
    )  # Medium/secondary models
    small_models = Column(JSON, nullable=False, default=list)  # Small/fallback models

    # Single model selection (for OpenAI strategies)
    selected_models = Column(
        JSON, nullable=False, default=list
    )  # Selected models for this provider

    # Priority for this provider in the strategy (lower number = higher priority)
    priority = Column(Integer, nullable=False, default=1)

    # Whether this provider is active in this strategy
    is_active = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    strategy = relationship("ModelStrategy", back_populates="provider_mappings")
    provider = relationship("Provider")


class Provider(Base):
    """Provider model"""

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
    verify_ssl = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)

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


class RequestStatistics(Base):
    """Request statistics tracking for providers and strategies"""

    __tablename__ = "request_statistics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Request tracking
    trace_id = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(100), nullable=False)  # /api/anthropic/v1/messages, /api/v1/chat/completions
    method = Column(String(10), nullable=False)  # POST, GET, etc.
    
    # Provider and strategy tracking
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    provider_name = Column(String(100), nullable=True)  # Denormalized for performance
    strategy_id = Column(Integer, ForeignKey("model_strategies.id"), nullable=True)
    strategy_name = Column(String(100), nullable=True)  # Denormalized for performance
    strategy_type = Column(String(20), nullable=True)  # anthropic, openai
    
    # Model information
    requested_model = Column(String(100), nullable=True)  # Original model requested
    actual_model = Column(String(100), nullable=True)  # Actual model used by provider
    model_tier = Column(String(20), nullable=True)  # small, medium, large
    
    # Request details
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Integer, nullable=False)  # Request duration in milliseconds
    request_size = Column(Integer, nullable=True)  # Request size in bytes
    response_size = Column(Integer, nullable=True)  # Response size in bytes
    
    # Token usage (if available)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Error tracking
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Client information
    client_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    provider = relationship("Provider")
    strategy = relationship("ModelStrategy")
    api_key = relationship("APIKey")
