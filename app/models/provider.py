from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    provider_type = Column(String(50), nullable=False)  # openai, azure, custom, etc.
    base_url = Column(String(500), nullable=False)
    api_key = Column(Text, nullable=False)
    model_list = Column(JSON, nullable=True)  # JSON array of available models
    big_model = Column(
        String(100), nullable=True
    )  # Model to use for "opus" class requests
    small_model = Column(
        String(100), nullable=True
    )  # Model to use for "haiku" class requests
    medium_model = Column(
        String(100), nullable=True
    )  # Model to use for "sonnet" class requests
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(
        Integer, default=1, nullable=False
    )  # Higher priority providers are used first
    max_tokens = Column(Integer, nullable=True)
    temperature_default = Column(String(10), nullable=True)
    headers = Column(JSON, nullable=True)  # Additional headers to send
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_name = Column(String(100), unique=True, index=True, nullable=False)
    api_key = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
