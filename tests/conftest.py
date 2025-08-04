"""
Test configuration and fixtures for pytest
"""

import asyncio
import os
import sys
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, get_db
from app.main import app
from app.models.strategy import APIKey, Provider
from app.schemas.provider import APIKeyCreate, ProviderCreate


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db():
    """Create a test database"""
    # Use in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create a session for the test
    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
def client(test_db):
    """Create a test client with overridden database dependency"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_api_key():
    """Create a test admin API key"""
    return "sk-test-admin-key-123456"


@pytest.fixture
def user_api_key():
    """Create a test user API key"""
    return "sk-test-user-key-789012"


@pytest_asyncio.fixture
async def test_admin_api_key(test_db):
    """Create a test admin API key in the database"""
    from app.utils.api_key_generator import generate_openai_style_api_key

    api_key = APIKey(
        key_name="test_admin_key",
        api_key="sk-test-admin-key-123456",
        description="Test admin key",
        is_admin=True,
        is_active=True,
    )

    test_db.add(api_key)
    await test_db.commit()
    await test_db.refresh(api_key)

    return api_key


@pytest_asyncio.fixture
async def test_user_api_key(test_db):
    """Create a test user API key in the database"""
    from app.utils.api_key_generator import generate_openai_style_api_key

    api_key = APIKey(
        key_name="test_user_key",
        api_key="sk-test-user-key-789012",
        description="Test user key",
        is_admin=False,
        is_active=True,
    )

    test_db.add(api_key)
    await test_db.commit()
    await test_db.refresh(api_key)

    return api_key


@pytest_asyncio.fixture
async def test_provider(test_db):
    """Create a test provider in the database"""
    provider = Provider(
        name="Test Provider",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-api-key",
        model_list=["gpt-4", "gpt-3.5-turbo"],
        is_active=True,
    )

    test_db.add(provider)
    await test_db.commit()
    await test_db.refresh(provider)

    return provider
