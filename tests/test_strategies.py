import pytest
from fastapi.testclient import TestClient

from app.models.strategy import ModelStrategy, Provider
from app.schemas.strategy import (
    ModelMappingRequest,
    ModelStrategyCreate,
    ModelStrategyUpdate,
)
from app.services.strategy_service import StrategyService


@pytest.mark.asyncio
class TestStrategyManagement:
    """Test strategy CRUD operations"""

    async def test_create_strategy_as_admin(
        self, client, test_admin_api_key, test_provider, test_db
    ):
        """Test creating a strategy as admin"""
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_admin_api_key.api_key}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create strategy with new multi-provider format
        strategy_data = {
            "name": "Test Anthropic Strategy",
            "description": "Test strategy for Anthropic models",
            "strategy_type": "anthropic",
            "fallback_enabled": True,
            "fallback_order": ["large", "medium", "small"],
            "provider_mappings": [
                {
                    "provider_id": test_provider.id,
                    "large_models": ["claude-3-opus-20240229"],
                    "medium_models": ["claude-3-sonnet-20240229"],
                    "small_models": ["claude-3-haiku-20240307"],
                    "selected_models": [],
                    "priority": 1,
                    "is_active": True,
                }
            ],
        }

        response = client.post(
            "/api/portal/strategies",
            json=strategy_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Anthropic Strategy"
        assert data["strategy_type"] == "anthropic"
        assert len(data["provider_mappings"]) == 1
        assert data["provider_mappings"][0]["large_models"] == [
            "claude-3-opus-20240229"
        ]
        assert data["fallback_enabled"] is True

    async def test_create_strategy_as_user_fails(self, client, test_user_api_key):
        """Test that non-admin users cannot create strategies"""
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_user_api_key.api_key}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        strategy_data = {
            "name": "Test Strategy",
            "strategy_type": "anthropic",
            "large_models": ["claude-3-opus-20240229"],
        }

        response = client.post(
            "/api/portal/strategies",
            json=strategy_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_get_strategies_as_user(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test getting strategies as regular user"""
        # First create a strategy as admin
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        await self._create_test_strategy(client, admin_token, test_provider.id)

        # Then get strategies as user
        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            "/api/portal/strategies", headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["strategy_type"] == "anthropic"

    async def test_get_strategies_filtered_by_type(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test filtering strategies by type"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        await self._create_test_strategy(client, admin_token, test_provider.id)

        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            "/api/portal/strategies?strategy_type=anthropic",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert all(strategy["strategy_type"] == "anthropic" for strategy in data)

    async def test_get_strategy_by_id(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test getting a specific strategy by ID"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        strategy = await self._create_test_strategy(
            client, admin_token, test_provider.id
        )

        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            f"/api/portal/strategies/{strategy['id']}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == strategy["id"]
        assert data["name"] == strategy["name"]

    async def test_update_strategy_as_admin(
        self, client, test_admin_api_key, test_provider, test_db
    ):
        """Test updating a strategy as admin"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        strategy = await self._create_test_strategy(
            client, admin_token, test_provider.id
        )

        update_data = {
            "name": "Updated Strategy Name",
            "description": "Updated description",
            "fallback_enabled": False,
        }

        response = client.put(
            f"/api/portal/strategies/{strategy['id']}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Strategy Name"
        assert data["fallback_enabled"] is False

    async def test_update_strategy_as_user_fails(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test that non-admin users cannot update strategies"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        strategy = await self._create_test_strategy(
            client, admin_token, test_provider.id
        )

        user_token = await self._get_portal_token(client, test_user_api_key)
        update_data = {"name": "Updated Strategy Name"}

        response = client.put(
            f"/api/portal/strategies/{strategy['id']}",
            json=update_data,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    async def test_delete_strategy_as_admin(
        self, client, test_admin_api_key, test_provider, test_db
    ):
        """Test deleting a strategy as admin"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        strategy = await self._create_test_strategy(
            client, admin_token, test_provider.id
        )

        response = client.delete(
            f"/api/portal/strategies/{strategy['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        # Verify it's deleted
        get_response = client.get(
            f"/api/portal/strategies/{strategy['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_response.status_code == 404

    async def test_delete_strategy_as_user_fails(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test that non-admin users cannot delete strategies"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        strategy = await self._create_test_strategy(
            client, admin_token, test_provider.id
        )

        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.delete(
            f"/api/portal/strategies/{strategy['id']}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    async def test_get_providers_with_strategies(
        self, client, test_user_api_key, test_db
    ):
        """Test getting providers with strategy information"""
        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            "/api/portal/providers-with-strategies",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:  # If there are providers
            provider = data[0]
            assert "id" in provider
            assert "name" in provider
            assert "model_list" in provider
            assert "strategy_id" in provider  # Should be None after refactoring

    async def test_get_strategies_with_providers(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test getting strategies with provider information"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        await self._create_test_strategy(client, admin_token, test_provider.id)

        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            "/api/portal/strategies-with-providers",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:  # If there are strategies
            strategy = data[0]
            assert "id" in strategy
            assert "name" in strategy
            assert "provider_mappings" in strategy
            assert "fallback_enabled" in strategy

    async def test_get_available_models_for_anthropic_strategy(
        self, client, test_user_api_key, test_provider, test_db
    ):
        """Test getting available models for Anthropic strategy"""
        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            "/api/portal/strategy-models?strategy_type=anthropic",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "providers" in data
        # Should include models from the test provider
        assert len(data["models"]) > 0
        assert len(data["providers"]) > 0

    async def test_get_available_models_for_openai_strategy(
        self, client, test_user_api_key, test_provider, test_db
    ):
        """Test getting available models for OpenAI strategy"""
        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            "/api/portal/strategy-models?strategy_type=openai",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "providers" in data
        # Should include models from the test provider
        assert len(data["models"]) > 0
        assert len(data["providers"]) > 0

    async def test_get_available_models_invalid_strategy_type(
        self, client, test_user_api_key
    ):
        """Test that invalid strategy_type returns error"""
        user_token = await self._get_portal_token(client, test_user_api_key)
        response = client.get(
            "/api/portal/strategy-models?strategy_type=invalid",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400

    async def test_model_mapping_anthropic(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test model mapping for Anthropic strategy"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        await self._create_test_strategy(client, admin_token, test_provider.id)

        user_token = await self._get_portal_token(client, test_user_api_key)
        mapping_request = {
            "strategy_type": "anthropic",
            "requested_model": "claude-3-sonnet-20240229",
            "preferred_tier": "medium",
        }

        response = client.post(
            "/api/portal/map-model",
            json=mapping_request,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        # This might fail if no providers are configured, but should return proper error
        assert response.status_code in [200, 400]

    async def test_model_mapping_openai(
        self, client, test_user_api_key, test_admin_api_key, test_provider, test_db
    ):
        """Test model mapping for OpenAI strategy"""
        admin_token = await self._get_portal_token(client, test_admin_api_key)
        await self._create_openai_strategy(client, admin_token, test_provider.id)

        user_token = await self._get_portal_token(client, test_user_api_key)
        mapping_request = {
            "strategy_type": "openai",
            "requested_model": "gpt-4",
        }

        response = client.post(
            "/api/portal/map-model",
            json=mapping_request,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        # This might fail if no providers are configured, but should return proper error
        assert response.status_code in [200, 400]

    async def test_model_mapping_invalid_strategy_type(self, client, test_user_api_key):
        """Test model mapping with invalid strategy type"""
        user_token = await self._get_portal_token(client, test_user_api_key)
        mapping_request = {
            "strategy_type": "invalid",
            "requested_model": "test-model",
        }

        response = client.post(
            "/api/portal/map-model",
            json=mapping_request,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 422

    # Helper methods
    async def _get_portal_token(self, client, api_key_fixture) -> str:
        """Get portal JWT token for authentication"""
        login_response = client.post(
            "/api/portal/login", json={"api_key": api_key_fixture.api_key}
        )
        assert login_response.status_code == 200
        return login_response.json()["access_token"]

    async def _create_test_strategy(
        self, client, admin_token: str, provider_id: int
    ) -> dict:
        """Create a test strategy and return it"""
        strategy_data = {
            "name": "Test Anthropic Strategy",
            "description": "Test strategy for Anthropic models",
            "strategy_type": "anthropic",
            "fallback_enabled": True,
            "fallback_order": ["large", "medium", "small"],
            "provider_mappings": [
                {
                    "provider_id": provider_id,
                    "large_models": ["claude-3-opus-20240229"],
                    "medium_models": ["claude-3-sonnet-20240229"],
                    "small_models": ["claude-3-haiku-20240307"],
                    "selected_models": [],
                    "priority": 1,
                    "is_active": True,
                }
            ],
        }

        response = client.post(
            "/api/portal/strategies",
            json=strategy_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        return response.json()

    async def _create_openai_strategy(
        self, client, admin_token: str, provider_id: int
    ) -> dict:
        """Create a test OpenAI strategy and return it"""
        strategy_data = {
            "name": "Test OpenAI Strategy",
            "description": "Test strategy for OpenAI models",
            "strategy_type": "openai",
            "fallback_enabled": True,
            "fallback_order": ["large", "medium", "small"],
            "provider_mappings": [
                {
                    "provider_id": provider_id,
                    "large_models": [],
                    "medium_models": [],
                    "small_models": [],
                    "selected_models": ["gpt-4"],
                    "priority": 1,
                    "is_active": True,
                }
            ],
        }

        response = client.post(
            "/api/portal/strategies",
            json=strategy_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        return response.json()
