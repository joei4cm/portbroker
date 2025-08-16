"""
Logging utilities with sensitive data filtering
"""

import re
import logging
import structlog
from typing import Any, Dict


class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    SENSITIVE_PATTERNS = [
        # Specific API key formats (should be processed first)
        (r'sk-[a-zA-Z0-9]{8,}', r'sk-***'),
        (r'sk-ant-[a-zA-Z0-9]{8,}', r'sk-ant-***'),
        (r'gsk_[a-zA-Z0-9]{8,}', r'gsk_***'),
        (r'pplx-[a-zA-Z0-9]{8,}', r'pplx-***'),
        
        # JWT tokens
        (r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', r'jwt.***'),
        
        # Generic API keys and tokens (process after specific formats)
        (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)[^"\'"\s]+', r'\1***'),
        (r'(authorization["\']?\s*[:=]\s*["\']?bearer\s+)[^"\'"\s]+', r'\1***', re.IGNORECASE),
        (r'(token["\']?\s*[:=]\s*["\']?)[^"\'"\s]+', r'\1***'),
        (r'(secret["\']?\s*[:=]\s*["\']?)[^"\'"\s]+', r'\1***'),
        (r'(password["\']?\s*[:=]\s*["\']?)[^"\'"\s]+', r'\1***'),
        
        # Database URLs with credentials
        (r'(postgresql://[^:]+:)[^@]+(@)', r'\1***\2'),
        (r'(mysql://[^:]+:)[^@]+(@)', r'\1***\2'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log record"""
        if hasattr(record, 'msg'):
            record.msg = self.filter_sensitive_data(record.msg)
        
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self.filter_sensitive_data(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def filter_sensitive_data(self, data: Any) -> Any:
        """Filter sensitive data from string data"""
        if not isinstance(data, str):
            return data
        
        filtered_data = data
        for pattern_data in self.SENSITIVE_PATTERNS:
            if len(pattern_data) == 3:
                pattern, replacement, flag_value = pattern_data
            else:
                pattern, replacement = pattern_data[:2]
                flag_value = 0
            filtered_data = re.sub(pattern, replacement, filtered_data, flags=flag_value)
        
        return filtered_data


def setup_structured_logging() -> None:
    """Setup structured logging with structlog"""
    
    # Add sensitive data filter to all handlers
    sensitive_filter = SensitiveDataFilter()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Add filter to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(sensitive_filter)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


def filter_dict_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter sensitive data from dictionary"""
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = {
        'api_key', 'apikey', 'secret', 'password', 'token', 'authorization',
        'secret_key', 'private_key', 'access_token', 'refresh_token'
    }
    
    filtered_data = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            filtered_data[key] = "***"
        elif isinstance(value, dict):
            filtered_data[key] = filter_dict_sensitive_data(value)
        elif isinstance(value, str):
            # Apply string filtering for nested sensitive data
            filter_instance = SensitiveDataFilter()
            filtered_data[key] = filter_instance.filter_sensitive_data(value)
        else:
            filtered_data[key] = value
    
    return filtered_data