"""
Test provider management functionality
"""

import pytest
from fastapi.testclient import TestClient


class TestProviderManagement:
    """Test provider CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_provider_as_admin(self, client, test_admin_api_key):
        """Test creating a provider as admin"""
        response = client.post(
            "/v1/providers",
            headers={"Authorization": f"Bearer {test_admin_api_key.api_key}"},
            json={
                "name": "Test Provider",
                "provider_type": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-api-key",
                "model_list": ["gpt-4", "gpt-3.5-turbo"],
                "priority": 1,
            },
        )

        # Should work with proper auth
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get_providers_as_user(self, client, test_user_api_key):
        """Test getting providers as regular user"""
        response = client.get(
            "/v1/providers",
            headers={"Authorization": f"Bearer {test_user_api_key.api_key}"},
        )

        # Should return 200 with proper auth
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_providers_unauthorized(self, client):
        """Test getting providers without authentication"""
        response = client.get("/v1/providers")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_provider_as_admin(
        self, client, test_admin_api_key, test_provider
    ):
        """Test updating a provider as admin"""
        response = client.put(
            f"/v1/providers/{test_provider.id}",
            headers={"Authorization": f"Bearer {test_admin_api_key.api_key}"},
            json={"name": "Updated Provider", "is_active": False},
        )

        # Should work with proper auth
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_provider_as_admin(
        self, client, test_admin_api_key, test_provider
    ):
        """Test deleting a provider as admin"""
        response = client.delete(
            f"/v1/providers/{test_provider.id}",
            headers={"Authorization": f"Bearer {test_admin_api_key.api_key}"},
        )

        # Should work with proper auth
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_provider_models(self, client, test_user_api_key, test_provider):
        """Test getting models from a specific provider"""
        response = client.get(
            f"/v1/providers/{test_provider.id}/models",
            headers={"Authorization": f"Bearer {test_user_api_key.api_key}"},
        )

        # Should return 200 with proper auth
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_all_models(self, client, test_user_api_key):
        """Test getting all models from all providers"""
        response = client.get(
            "/v1/models",
            headers={"Authorization": f"Bearer {test_user_api_key.api_key}"},
        )

        # Should return 200 with proper auth
        assert response.status_code == 200
