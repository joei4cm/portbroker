"""
Test duplicate provider name validation
"""
import pytest
from app.models.strategy import Provider
from app.core.database import AsyncSessionLocal
from sqlalchemy import select


class TestDuplicateProviderValidation:
    """Test duplicate provider name validation"""

    @pytest.mark.asyncio
    async def test_create_duplicate_provider_name(self, client, test_admin_api_key):
        """Test that creating a provider with duplicate name fails gracefully"""
        import uuid
        
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_admin_api_key.api_key}
        )
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create first provider
        provider_data = {
            "name": f"Duplicate Test Provider {uuid.uuid4().hex[:8]}",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "test-key-123",
            "model_list": ["gpt-4"],
            "verify_ssl": True,
            "is_active": True
        }
        
        response = client.post("/api/portal/providers", headers=headers, json=provider_data)
        assert response.status_code == 200
        
        # Try to create provider with same name
        response = client.post("/api/portal/providers", headers=headers, json=provider_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
        
        # Clean up
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Provider).where(Provider.name == provider_data["name"]))
            provider = result.scalar_one_or_none()
            if provider:
                await db.delete(provider)
                await db.commit()

    @pytest.mark.asyncio
    async def test_update_provider_duplicate_name(self, client, test_admin_api_key):
        """Test that updating a provider to a duplicate name fails gracefully"""
        import uuid
        
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_admin_api_key.api_key}
        )
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create first provider
        provider_data1 = {
            "name": f"Original Provider {uuid.uuid4().hex[:8]}",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "test-key-123",
            "model_list": ["gpt-4"],
            "verify_ssl": True,
            "is_active": True
        }
        
        response = client.post("/api/portal/providers", headers=headers, json=provider_data1)
        assert response.status_code == 200
        provider1_id = response.json()["id"]
        
        # Create second provider
        provider_data2 = {
            "name": f"Second Provider {uuid.uuid4().hex[:8]}",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "test-key-456",
            "model_list": ["gpt-4"],
            "verify_ssl": True,
            "is_active": True
        }
        
        response = client.post("/api/portal/providers", headers=headers, json=provider_data2)
        assert response.status_code == 200
        provider2_id = response.json()["id"]
        
        # Try to update second provider with first provider's name
        update_data = {"name": provider_data1["name"]}
        response = client.put(f"/api/portal/providers/{provider2_id}", headers=headers, json=update_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
        
        # Clean up
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Provider).where(Provider.id.in_([provider1_id, provider2_id])))
            providers = result.scalars().all()
            for provider in providers:
                await db.delete(provider)
            await db.commit()