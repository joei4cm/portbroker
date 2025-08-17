"""
Test API endpoints
"""

import pytest
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Test the main API endpoints"""

    def test_chat_completions_endpoint(self, client):
        """Test the chat completions endpoint"""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello, world!"}],
                "max_tokens": 50,
            },
        )

        # Should return 403 if no API key is provided (HTTPBearer security)
        assert response.status_code == 403

    def test_anthropic_messages_endpoint(self, client):
        """Test the Anthropic messages endpoint"""
        response = client.post(
            "/api/anthropic/v1/messages",
            json={
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Hello, world!"}],
            },
        )

        # Should return 403 if no API key is provided (HTTPBearer security)
        assert response.status_code == 403

    def test_health_check(self, client):
        """Test the health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_endpoint(self, client):
        """Test the root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "PortBroker API", "version": "0.1.0"}
