"""
Test for API key regeneration functionality
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.models.strategy import APIKey
from app.utils.api_key_generator import generate_openai_style_api_key


class TestAPIKeyRegeneration:
    """Test API key regeneration functionality"""

    @pytest.mark.asyncio
    async def test_regenerate_api_key_as_admin(self, client, test_admin_api_key, test_db):
        """Test that admin can regenerate an API key"""
        # First create an API key
        from app.utils.api_key_generator import generate_openai_style_api_key
        from datetime import datetime, timedelta
        
        original_key_value = generate_openai_style_api_key()
        api_key = APIKey(
            key_name="test_key_for_regenerate",
            api_key=original_key_value,
            description="Test key for regeneration",
            is_active=True,
            is_admin=False,
            expires_at=datetime.now() + timedelta(days=30)
        )
        
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)
        
        key_id = api_key.id

        # Now regenerate the key
        regenerate_response = client.put(
            f"/v1/api-keys/{key_id}",
            json={"regenerate": True},
            headers={"Authorization": f"Bearer {test_admin_api_key.api_key}"}
        )
        assert regenerate_response.status_code == 200
        regenerated_key = regenerate_response.json()
        
        # Verify the key was actually regenerated (different from original)
        assert regenerated_key["api_key"] != original_key_value
        assert regenerated_key["api_key"].startswith("sk-")
        assert len(regenerated_key["api_key"]) > 20  # Ensure it's a proper key
        
        # Verify other fields remain unchanged
        assert regenerated_key["key_name"] == "test_key_for_regenerate"
        assert regenerated_key["description"] == "Test key for regeneration"
        assert regenerated_key["is_active"] == True
        assert regenerated_key["is_admin"] == False

    @pytest.mark.asyncio
    async def test_regenerate_api_key_non_admin_forbidden(self, client, test_user_api_key, test_db):
        """Test that non-admin cannot regenerate an API key"""
        # First create an API key
        from app.utils.api_key_generator import generate_openai_style_api_key
        from datetime import datetime, timedelta
        
        api_key = APIKey(
            key_name="test_key_non_admin",
            api_key=generate_openai_style_api_key(),
            description="Test key for non-admin",
            is_active=True,
            is_admin=False,
            expires_at=datetime.now() + timedelta(days=30)
        )
        
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)
        
        key_id = api_key.id
        
        # Try to regenerate (should fail)
        regenerate_response = client.put(
            f"/v1/api-keys/{key_id}",
            json={"regenerate": True},
            headers={"Authorization": f"Bearer {test_user_api_key.api_key}"}
        )
        assert regenerate_response.status_code == 403

    @pytest.mark.asyncio
    async def test_regenerate_nonexistent_key(self, client, test_admin_api_key):
        """Test that regenerating a non-existent key returns 404"""
        regenerate_response = client.put(
            "/v1/api-keys/99999",
            json={"regenerate": True},
            headers={"Authorization": f"Bearer {test_admin_api_key.api_key}"}
        )
        assert regenerate_response.status_code == 404

    @pytest.mark.asyncio
    async def test_regenerate_with_other_fields(self, client, test_admin_api_key, test_db):
        """Test that regeneration works alongside other field updates"""
        # First create an API key
        from app.utils.api_key_generator import generate_openai_style_api_key
        from datetime import datetime, timedelta
        
        original_key_value = generate_openai_style_api_key()
        api_key = APIKey(
            key_name="test_key_combined",
            api_key=original_key_value,
            description="Test key for combined update",
            is_active=True,
            is_admin=False,
            expires_at=datetime.now() + timedelta(days=30)
        )
        
        test_db.add(api_key)
        await test_db.commit()
        await test_db.refresh(api_key)
        
        key_id = api_key.id

        # Regenerate and update other fields
        update_response = client.put(
            f"/v1/api-keys/{key_id}",
            json={
                "regenerate": True,
                "key_name": "updated_key_name",
                "description": "Updated description",
                "is_active": False
            },
            headers={"Authorization": f"Bearer {test_admin_api_key.api_key}"}
        )
        assert update_response.status_code == 200
        updated_key = update_response.json()
        
        # Verify the key was regenerated
        assert updated_key["api_key"] != original_key_value
        assert updated_key["api_key"].startswith("sk-")
        
        # Verify other fields were updated
        assert updated_key["key_name"] == "updated_key_name"
        assert updated_key["description"] == "Updated description"
        assert updated_key["is_active"] == False