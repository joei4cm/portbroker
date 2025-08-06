import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.strategy import APIKey
from app.utils.api_key_generator import generate_openai_style_api_key

async def create_test_api_key():
    async with AsyncSessionLocal() as db:
        # Check if admin key already exists
        result = await db.execute(
            select(APIKey).where(APIKey.key_name == "test-admin-key")
        )
        existing_key = result.scalar_one_or_none()
        
        if existing_key:
            print(f"Admin key already exists: {existing_key.api_key}")
            return existing_key.api_key
        
        # Create a new admin API key
        api_key = generate_openai_style_api_key()
        
        db_key = APIKey(
            key_name="test-admin-key",
            api_key=api_key,
            description="Test admin key for portal testing",
            is_active=True,
            is_admin=True
        )
        
        db.add(db_key)
        await db.commit()
        await db.refresh(db_key)
        
        print(f"Created admin API key: {api_key}")
        return api_key

if __name__ == "__main__":
    key = asyncio.run(create_test_api_key())
    print(f"Use this key for testing: {key}")