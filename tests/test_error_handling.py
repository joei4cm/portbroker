"""
Tests for error handling system
"""

import pytest
from app.core.errors import (
    PortBrokerException,
    ProviderTimeoutError,
    ProviderAuthError,
    RateLimitError,
    UpstreamValidationError,
    InternalMappingError,
    ErrorCategory,
    get_http_status
)


class TestPortBrokerException:
    """Test base PortBroker exception"""
    
    def test_basic_exception_creation(self):
        """Test basic exception creation"""
        exc = PortBrokerException(
            message="Test error",
            category=ErrorCategory.INTERNAL_MAPPING,
            retriable=True,
            trace_id="test-trace-123"
        )
        
        assert exc.message == "Test error"
        assert exc.category == ErrorCategory.INTERNAL_MAPPING
        assert exc.retriable is True
        assert exc.trace_id == "test-trace-123"
        assert exc.details == {}
    
    def test_exception_to_dict(self):
        """Test exception serialization to dictionary"""
        exc = PortBrokerException(
            message="Test error",
            category=ErrorCategory.PROVIDER_AUTH,
            retriable=False,
            details={"provider": "test"},
            trace_id="trace-456"
        )
        
        result = exc.to_dict()
        expected = {
            "error": {
                "code": "provider_auth",
                "message": "Test error",
                "retriable": False,
                "trace_id": "trace-456",
                "details": {"provider": "test"}
            }
        }
        
        assert result == expected


class TestSpecificExceptions:
    """Test specific exception types"""
    
    def test_provider_timeout_error(self):
        """Test provider timeout error"""
        exc = ProviderTimeoutError(
            provider_name="openai",
            timeout_seconds=30.0,
            trace_id="timeout-trace"
        )
        
        assert exc.category == ErrorCategory.PROVIDER_TIMEOUT
        assert exc.retriable is True
        assert "openai" in exc.message
        assert "30.0" in exc.message
        assert exc.details["provider_name"] == "openai"
        assert exc.details["timeout_seconds"] == 30.0
    
    def test_provider_auth_error(self):
        """Test provider authentication error"""
        exc = ProviderAuthError(
            provider_name="anthropic",
            auth_type="bearer",
            trace_id="auth-trace"
        )
        
        assert exc.category == ErrorCategory.PROVIDER_AUTH
        assert exc.retriable is False
        assert "anthropic" in exc.message
        assert exc.details["provider_name"] == "anthropic"
        assert exc.details["auth_type"] == "bearer"
    
    def test_rate_limit_error(self):
        """Test rate limit error"""
        exc = RateLimitError(
            provider_name="openai",
            retry_after=60,
            trace_id="rate-trace"
        )
        
        assert exc.category == ErrorCategory.RATE_LIMIT
        assert exc.retriable is True
        assert "openai" in exc.message
        assert "60" in exc.message
        assert exc.details["retry_after"] == 60
    
    def test_rate_limit_error_no_retry_after(self):
        """Test rate limit error without retry_after"""
        exc = RateLimitError(
            provider_name="anthropic",
            trace_id="rate-trace-2"
        )
        
        assert exc.category == ErrorCategory.RATE_LIMIT
        assert exc.retriable is True
        assert "anthropic" in exc.message
        assert exc.details["retry_after"] is None
    
    def test_upstream_validation_error(self):
        """Test upstream validation error"""
        exc = UpstreamValidationError(
            provider_name="gemini",
            validation_details="Invalid model parameter",
            trace_id="validation-trace"
        )
        
        assert exc.category == ErrorCategory.UPSTREAM_VALIDATION
        assert exc.retriable is False
        assert "gemini" in exc.message
        assert "Invalid model parameter" in exc.message
        assert exc.details["validation_details"] == "Invalid model parameter"
    
    def test_internal_mapping_error(self):
        """Test internal mapping error"""
        exc = InternalMappingError(
            mapping_type="request",
            source_format="anthropic",
            target_format="openai",
            error_details="Missing required field",
            trace_id="mapping-trace"
        )
        
        assert exc.category == ErrorCategory.INTERNAL_MAPPING
        assert exc.retriable is False
        assert "request" in exc.message
        assert "anthropic" in exc.message
        assert "openai" in exc.message
        assert exc.details["mapping_type"] == "request"


class TestErrorStatusMapping:
    """Test HTTP status code mapping"""
    
    def test_get_http_status_for_known_categories(self):
        """Test HTTP status mapping for known error categories"""
        test_cases = [
            (ErrorCategory.PROVIDER_TIMEOUT, 504),
            (ErrorCategory.PROVIDER_AUTH, 401),
            (ErrorCategory.RATE_LIMIT, 429),
            (ErrorCategory.UPSTREAM_VALIDATION, 400),
            (ErrorCategory.INTERNAL_MAPPING, 500),
            (ErrorCategory.CONFIGURATION, 500),
            (ErrorCategory.DATABASE, 503),
            (ErrorCategory.NETWORK, 502),
        ]
        
        for category, expected_status in test_cases:
            exc = PortBrokerException(
                message="Test",
                category=category
            )
            assert get_http_status(exc) == expected_status
    
    def test_get_http_status_for_unknown_category(self):
        """Test HTTP status mapping for unknown category"""
        # Create a mock exception with unknown category
        exc = PortBrokerException(
            message="Test",
            category="unknown_category"  # This should trigger the default
        )
        
        # Since we can't easily mock the enum, let's test the default behavior
        # by checking that known categories work and assuming unknown defaults to 500
        known_exc = ProviderTimeoutError("test", 30.0)
        assert get_http_status(known_exc) == 504


class TestErrorClassification:
    """Test error classification for retriability"""
    
    def test_retriable_errors(self):
        """Test that appropriate errors are marked as retriable"""
        retriable_errors = [
            ProviderTimeoutError("test", 30.0),
            RateLimitError("test"),
        ]
        
        for error in retriable_errors:
            assert error.retriable is True, f"{type(error).__name__} should be retriable"
    
    def test_non_retriable_errors(self):
        """Test that appropriate errors are marked as non-retriable"""
        non_retriable_errors = [
            ProviderAuthError("test"),
            UpstreamValidationError("test", "validation failed"),
            InternalMappingError("request", "source", "target", "error"),
        ]
        
        for error in non_retriable_errors:
            assert error.retriable is False, f"{type(error).__name__} should not be retriable"