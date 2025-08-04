"""
Test utilities and helper functions
"""

import pytest

from app.utils.api_key_generator import (
    generate_expiration_date,
    generate_openai_style_api_key,
)


class TestAPIKeyGenerator:
    """Test API key generation utilities"""

    def test_generate_openai_style_api_key(self):
        """Test OpenAI-style API key generation"""
        key = generate_openai_style_api_key()

        # Check that key starts with 'sk-'
        assert key.startswith("sk-")

        # Check that key is reasonably long
        assert len(key) > 20

        # Check that key contains only allowed characters
        assert all(
            c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
            for c in key[3:]
        )

    def test_generate_expiration_date_none(self):
        """Test expiration date generation with None"""
        result = generate_expiration_date(None)
        assert result is None

    def test_generate_expiration_date_zero(self):
        """Test expiration date generation with 0"""
        result = generate_expiration_date(0)
        assert result is None

    def test_generate_expiration_date_positive(self):
        """Test expiration date generation with positive days"""
        import datetime

        result = generate_expiration_date(7)

        assert result is not None
        assert isinstance(result, datetime.datetime)

        # Check that expiration is in the future
        assert result > datetime.datetime.now(result.tzinfo)

    def test_generate_expiration_date_negative(self):
        """Test expiration date generation with negative days"""
        result = generate_expiration_date(-1)
        assert result is None
