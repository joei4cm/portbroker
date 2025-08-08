"""
Test provider service functionality
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.provider_service import ProviderService


class TestProviderService:
    """Test the provider service"""

    @pytest.mark.asyncio
    async def test_get_active_providers(self, test_db):
        """Test getting active providers"""
        # Add a test provider to the database
        import uuid

        from app.models.strategy import Provider

        provider = Provider(
            name=f"Test Provider {uuid.uuid4().hex[:8]}",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model_list=["gpt-4"],
            is_active=True,
        )
        test_db.add(provider)
        await test_db.commit()

        result = await ProviderService.get_active_providers(test_db)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name.startswith("Test Provider")

    @pytest.mark.asyncio
    async def test_get_provider_by_id(self, test_db):
        """Test getting provider by ID"""
        # Add a test provider to the database
        import uuid

        from app.models.strategy import Provider

        provider = Provider(
            name=f"Test Provider {uuid.uuid4().hex[:8]}",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model_list=["gpt-4"],
            is_active=True,
        )
        test_db.add(provider)
        await test_db.commit()
        await test_db.refresh(provider)

        result = await ProviderService.get_provider_by_id(test_db, provider.id)

        assert result is not None
        assert result.name.startswith("Test Provider")

        # Test with non-existent ID
        result = await ProviderService.get_provider_by_id(test_db, 999)
        assert result is None

    @pytest.mark.asyncio
    async def test_call_provider_api_success(self, test_db):
        """Test successful provider API call"""
        # Create a mock provider
        provider = Mock()
        provider.base_url = "https://api.openai.com/v1"
        provider.api_key = "test-key"
        provider.headers = {}
        provider.model_list = ["gpt-4"]
        provider.small_model = None
        provider.medium_model = None
        provider.big_model = None

        # Mock request
        request = Mock()
        request.model = "claude-3-sonnet"
        request.model_dump.return_value = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        # Mock httpx response
        with patch("app.services.provider_service.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"id": "test-response"}
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await ProviderService.call_provider_api(provider, request, False)

            assert result == {"id": "test-response"}

    @pytest.mark.asyncio
    async def test_call_provider_api_streaming(self, test_db):
        """Test streaming provider API call"""
        # Create a mock provider
        provider = Mock()
        provider.base_url = "https://api.openai.com/v1"
        provider.api_key = "test-key"
        provider.headers = {}
        provider.model_list = ["gpt-4"]
        provider.small_model = None
        provider.medium_model = None
        provider.big_model = None

        # Mock request
        request = Mock()
        request.model = "claude-3-sonnet"
        request.model_dump.return_value = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        # Mock httpx response
        with patch("app.services.provider_service.httpx.AsyncClient") as mock_client:
            mock_response = Mock()

            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await ProviderService.call_provider_api(provider, request, True)

            assert result == mock_response

    @pytest.mark.asyncio
    async def test_try_providers_until_success(self, test_db):
        """Test trying providers until success"""
        # Mock provider list
        with patch.object(
            ProviderService, "get_active_providers"
        ) as mock_get_providers:
            mock_get_providers.return_value = [Mock(), Mock()]

            # Mock successful API call
            with patch.object(ProviderService, "call_provider_api") as mock_call:
                mock_call.return_value = {"id": "success"}

                request = Mock()
                result = await ProviderService.try_providers_until_success(
                    test_db, request, False
                )

                assert result == {"id": "success"}
                mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_providers_until_all_fail(self, test_db):
        """Test trying providers when all fail"""
        # Mock provider list
        with patch.object(
            ProviderService, "get_active_providers"
        ) as mock_get_providers:
            mock_get_providers.return_value = [Mock(), Mock()]

            # Mock failed API calls
            with patch.object(ProviderService, "call_provider_api") as mock_call:
                mock_call.side_effect = Exception("Provider failed")

                request = Mock()

                with pytest.raises(Exception) as exc_info:
                    await ProviderService.try_providers_until_success(
                        test_db, request, False
                    )

                assert "All providers failed" in str(exc_info.value)
                assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_try_providers_no_providers(self, test_db):
        """Test trying providers when none are available"""
        # Mock empty provider list
        with patch.object(
            ProviderService, "get_active_providers"
        ) as mock_get_providers:
            mock_get_providers.return_value = []

            request = Mock()

            with pytest.raises(Exception) as exc_info:
                await ProviderService.try_providers_until_success(
                    test_db, request, False
                )

            assert "No active providers available" in str(exc_info.value)
