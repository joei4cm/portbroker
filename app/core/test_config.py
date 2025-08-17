"""
Test configuration module for PortBroker

This module provides separate database configuration for testing
to ensure tests don't affect production data.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class TestSettings(BaseSettings):
    """Test-specific settings"""
    
    # Test database configuration
    test_database_type: str = "sqlite"
    test_database_url: str = "sqlite:///./portbroker_test.db"
    
    # Test environment flag
    testing: bool = True
    
    # Allow extra fields from environment
    class Config:
        env_file = ".env.test"
        env_prefix = "TEST_"
        extra = "allow"


def get_test_database_url() -> str:
    """Get the test database URL based on environment configuration"""
    test_settings = TestSettings()
    
    # Allow override via environment variable
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    
    return test_settings.test_database_url


def get_test_database_type() -> str:
    """Get the test database type based on environment configuration"""
    test_settings = TestSettings()
    
    # Allow override via environment variable
    if os.getenv("TEST_DATABASE_TYPE"):
        return os.getenv("TEST_DATABASE_TYPE")
    
    return test_settings.test_database_type


# Test database configuration
TEST_DATABASE_URL = get_test_database_url()
TEST_DATABASE_TYPE = get_test_database_type()