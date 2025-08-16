"""
Unified error handling system for PortBroker
Provides structured exception hierarchy and error mapping
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCategory(str, Enum):
    """Error categories for classification and handling"""
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_AUTH = "provider_auth"
    RATE_LIMIT = "rate_limit"
    UPSTREAM_VALIDATION = "upstream_validation"
    INTERNAL_MAPPING = "internal_mapping"
    CONFIGURATION = "configuration"
    DATABASE = "database"
    NETWORK = "network"


class PortBrokerException(Exception):
    """Base exception for all PortBroker errors"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        retriable: bool = False,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.retriable = retriable
        self.details = details or {}
        self.trace_id = trace_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization"""
        return {
            "error": {
                "code": self.category.value,
                "message": self.message,
                "retriable": self.retriable,
                "trace_id": self.trace_id,
                "details": self.details
            }
        }


class ProviderTimeoutError(PortBrokerException):
    """Provider request timeout error"""
    
    def __init__(
        self,
        provider_name: str,
        timeout_seconds: float,
        trace_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Provider '{provider_name}' timed out after {timeout_seconds}s",
            category=ErrorCategory.PROVIDER_TIMEOUT,
            retriable=True,
            details={"provider_name": provider_name, "timeout_seconds": timeout_seconds},
            trace_id=trace_id
        )


class ProviderAuthError(PortBrokerException):
    """Provider authentication error"""
    
    def __init__(
        self,
        provider_name: str,
        auth_type: str = "api_key",
        trace_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Authentication failed for provider '{provider_name}'",
            category=ErrorCategory.PROVIDER_AUTH,
            retriable=False,
            details={"provider_name": provider_name, "auth_type": auth_type},
            trace_id=trace_id
        )


class RateLimitError(PortBrokerException):
    """Rate limit exceeded error"""
    
    def __init__(
        self,
        provider_name: str,
        retry_after: Optional[int] = None,
        trace_id: Optional[str] = None
    ):
        retry_msg = f" (retry after {retry_after}s)" if retry_after else ""
        super().__init__(
            message=f"Rate limit exceeded for provider '{provider_name}'{retry_msg}",
            category=ErrorCategory.RATE_LIMIT,
            retriable=True,
            details={"provider_name": provider_name, "retry_after": retry_after},
            trace_id=trace_id
        )


class UpstreamValidationError(PortBrokerException):
    """Upstream provider validation error"""
    
    def __init__(
        self,
        provider_name: str,
        validation_details: str,
        trace_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Provider '{provider_name}' validation error: {validation_details}",
            category=ErrorCategory.UPSTREAM_VALIDATION,
            retriable=False,
            details={"provider_name": provider_name, "validation_details": validation_details},
            trace_id=trace_id
        )


class InternalMappingError(PortBrokerException):
    """Internal model/request mapping error"""
    
    def __init__(
        self,
        mapping_type: str,
        source_format: str,
        target_format: str,
        error_details: str,
        trace_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Failed to map {mapping_type} from {source_format} to {target_format}: {error_details}",
            category=ErrorCategory.INTERNAL_MAPPING,
            retriable=False,
            details={
                "mapping_type": mapping_type,
                "source_format": source_format,
                "target_format": target_format,
                "error_details": error_details
            },
            trace_id=trace_id
        )


class ConfigurationError(PortBrokerException):
    """Configuration error"""
    
    def __init__(
        self,
        config_key: str,
        error_details: str,
        trace_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Configuration error for '{config_key}': {error_details}",
            category=ErrorCategory.CONFIGURATION,
            retriable=False,
            details={"config_key": config_key, "error_details": error_details},
            trace_id=trace_id
        )


class DatabaseError(PortBrokerException):
    """Database operation error"""
    
    def __init__(
        self,
        operation: str,
        error_details: str,
        retriable: bool = True,
        trace_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Database {operation} error: {error_details}",
            category=ErrorCategory.DATABASE,
            retriable=retriable,
            details={"operation": operation, "error_details": error_details},
            trace_id=trace_id
        )


class NetworkError(PortBrokerException):
    """Network connectivity error"""
    
    def __init__(
        self,
        endpoint: str,
        error_details: str,
        trace_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Network error connecting to {endpoint}: {error_details}",
            category=ErrorCategory.NETWORK,
            retriable=True,
            details={"endpoint": endpoint, "error_details": error_details},
            trace_id=trace_id
        )


# Error code to HTTP status mapping
ERROR_STATUS_MAP = {
    ErrorCategory.PROVIDER_TIMEOUT: 504,  # Gateway Timeout
    ErrorCategory.PROVIDER_AUTH: 401,     # Unauthorized
    ErrorCategory.RATE_LIMIT: 429,        # Too Many Requests
    ErrorCategory.UPSTREAM_VALIDATION: 400,  # Bad Request
    ErrorCategory.INTERNAL_MAPPING: 500,  # Internal Server Error
    ErrorCategory.CONFIGURATION: 500,     # Internal Server Error
    ErrorCategory.DATABASE: 503,          # Service Unavailable
    ErrorCategory.NETWORK: 502,           # Bad Gateway
}


def get_http_status(error: PortBrokerException) -> int:
    """Get HTTP status code for a PortBroker exception"""
    return ERROR_STATUS_MAP.get(error.category, 500)