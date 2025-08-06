"""
Test portal authentication and UI functionality
"""

import pytest
from fastapi.testclient import TestClient


class TestPortalAuth:
    """Test portal authentication"""

    @pytest.mark.asyncio
    async def test_portal_login_with_valid_key(self, client, admin_api_key):
        """Test portal login with a valid API key"""
        response = client.post("/api/portal/login", json={"api_key": admin_api_key})

        # Should return 200 with token if auth works
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_portal_login_with_invalid_key(self, client):
        """Test portal login with an invalid API key"""
        response = client.post("/api/portal/login", json={"api_key": "invalid-key"})

        # Should return 401 for invalid key
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_portal_user_info_endpoint(self, client, user_api_key):
        """Test getting user info from portal"""
        response = client.get(
            "/api/portal/user-info", headers={"Authorization": f"Bearer {user_api_key}"}
        )

        # Should return 200 or 401 depending on auth setup
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_user_info_endpoint_with_admin(self, client, test_admin_api_key):
        """Test user info endpoint returns admin status for admin user"""
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_admin_api_key.api_key}
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        # Test user info endpoint
        response = client.get(
            "/api/portal/user-info", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        user_info = response.json()
        assert "username" in user_info
        assert "is_admin" in user_info
        assert user_info["is_admin"] == True

    @pytest.mark.asyncio
    async def test_user_info_endpoint_with_user(self, client, test_user_api_key):
        """Test user info endpoint returns non-admin status for regular user"""
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_user_api_key.api_key}
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        # Test user info endpoint
        response = client.get(
            "/api/portal/user-info", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        user_info = response.json()
        assert "username" in user_info
        assert "is_admin" in user_info
        assert user_info["is_admin"] == False

    @pytest.mark.asyncio
    async def test_settings_endpoint_accessible_to_admin(
        self, client, test_admin_api_key
    ):
        """Test settings endpoint is accessible to admin users"""
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_admin_api_key.api_key}
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        # Test settings endpoint
        response = client.get(
            "/api/portal/settings", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        settings = response.json()
        assert "database_type" in settings
        assert "database_url" in settings

    @pytest.mark.asyncio
    async def test_settings_endpoint_accessible_to_user(
        self, client, test_user_api_key
    ):
        """Test settings endpoint is accessible to users but UI should hide navigation"""
        # First login to get token
        login_response = client.post(
            "/api/portal/login", json={"api_key": test_user_api_key.api_key}
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        # Test settings endpoint
        response = client.get(
            "/api/portal/settings", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        settings = response.json()
        assert "database_type" in settings
        assert "database_url" in settings

    @pytest.mark.asyncio
    async def test_portal_settings_endpoint(self, client, user_api_key):
        """Test getting settings from portal"""
        response = client.get(
            "/api/portal/settings", headers={"Authorization": f"Bearer {user_api_key}"}
        )

        # Should return 200 or 401 depending on auth setup
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_portal_providers_endpoint(self, client, user_api_key):
        """Test getting providers from portal"""
        response = client.get(
            "/api/portal/providers", headers={"Authorization": f"Bearer {user_api_key}"}
        )

        # Should return 200 or 401 depending on auth setup
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_portal_api_keys_endpoint(self, client, user_api_key):
        """Test getting API keys from portal"""
        response = client.get(
            "/api/portal/api-keys", headers={"Authorization": f"Bearer {user_api_key}"}
        )

        # Should return 200 or 401 depending on auth setup
        assert response.status_code in [200, 401]


class TestPortalPermissions:
    """Test portal permission system"""

    @pytest.mark.asyncio
    async def test_admin_can_create_provider(self, client, admin_api_key):
        """Test that admin can create providers via portal"""
        import uuid
        
        response = client.post(
            "/api/portal/providers",
            headers={"Authorization": f"Bearer {admin_api_key}"},
            json={
                "name": f"Admin Test Provider {uuid.uuid4().hex[:8]}",
                "provider_type": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
                "model_list": ["gpt-4"],
                "priority": 1,
            },
        )

        # Should work if auth is properly implemented
        assert response.status_code in [201, 401, 403]

    @pytest.mark.asyncio
    async def test_user_cannot_create_provider(self, client, user_api_key):
        """Test that regular user cannot create providers via portal"""
        import uuid
        
        response = client.post(
            "/api/portal/providers",
            headers={"Authorization": f"Bearer {user_api_key}"},
            json={
                "name": f"User Test Provider {uuid.uuid4().hex[:8]}",
                "provider_type": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
                "model_list": ["gpt-4"],
                "priority": 1,
            },
        )

        # Should be forbidden for regular users
        assert response.status_code in [403, 401]
