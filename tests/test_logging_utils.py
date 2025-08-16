"""
Tests for logging utilities and sensitive data filtering
"""

import logging
import pytest
from app.core.logging_utils import SensitiveDataFilter, filter_dict_sensitive_data


class TestSensitiveDataFilter:
    """Test sensitive data filtering"""
    
    def test_api_key_filtering(self):
        """Test API key filtering"""
        filter_instance = SensitiveDataFilter()
        
        test_cases = [
            # Basic API key patterns - field name : value pairs get filtered generically
            ('api_key: sk-1234567890abcdef', 'api_key: ***'),
            ('api-key="sk-ant-1234567890"', 'api-key="***"'),
            ('apikey=gsk_1234567890', 'apikey=***'),
            ('token: pplx-1234567890', 'token: ***'),
            
            # Specific API key formats in different contexts
            ('Error: sk-1234567890abcdef is invalid', 'Error: sk-*** is invalid'),
            ('Using sk-ant-1234567890', 'Using sk-ant-***'),
            ('Key: gsk_1234567890', 'Key: gsk_***'),
            ('Token pplx-1234567890', 'Token pplx-***'),
            
            # Authorization headers
            ('Authorization: Bearer sk-1234567890', 'Authorization: Bearer ***'),
            ('authorization="bearer sk-ant-test123"', 'authorization="bearer ***"'),
            
            # Secret and password fields
            ('secret: mysecretvalue', 'secret: ***'),
            ('password="mypassword123"', 'password="***"'),
            
            # JWT tokens - when following "token:" gets filtered generically
            ('token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c', 
             'token: ***'),
            # JWT tokens in other contexts get specific replacement
            ('JWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
             'JWT jwt.***'),
            
            # Database URLs
            ('DATABASE_URL=postgresql://user:password@host/db', 'DATABASE_URL=postgresql://user:***@host/db'),
            ('mysql://admin:secret123@localhost/mydb', 'mysql://admin:***@localhost/mydb'),
        ]
        
        for input_text, expected in test_cases:
            result = filter_instance.filter_sensitive_data(input_text)
            assert result == expected, f"Failed for input: {input_text}"
    
    def test_log_record_filtering(self):
        """Test log record filtering"""
        filter_instance = SensitiveDataFilter()
        
        # Create a log record with sensitive data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="API call with api_key: sk-1234567890",
            args=("secret: mysecret",),
            exc_info=None
        )
        
        # Apply filter
        result = filter_instance.filter(record)
        
        assert result is True  # Filter should always return True
        assert "api_key: ***" in record.msg
        assert record.args[0] == "secret: ***"
    
    def test_non_string_data_passthrough(self):
        """Test that non-string data passes through unchanged"""
        filter_instance = SensitiveDataFilter()
        
        test_data = [123, {"key": "value"}, None, True]
        
        for data in test_data:
            result = filter_instance.filter_sensitive_data(data)
            assert result == data
    
    def test_case_insensitive_filtering(self):
        """Test case-insensitive filtering for authorization headers"""
        filter_instance = SensitiveDataFilter()
        
        test_cases = [
            'Authorization: Bearer sk-test123',
            'AUTHORIZATION: Bearer sk-test123',
            'authorization: bearer sk-test123',
        ]
        
        for case in test_cases:
            result = filter_instance.filter_sensitive_data(case)
            assert "***" in result
            assert "sk-test123" not in result


class TestDictSensitiveDataFilter:
    """Test dictionary sensitive data filtering"""
    
    def test_basic_dict_filtering(self):
        """Test basic dictionary filtering"""
        input_dict = {
            "api_key": "sk-1234567890",
            "username": "testuser",
            "secret": "mysecret",
            "normal_field": "normal_value"
        }
        
        result = filter_dict_sensitive_data(input_dict)
        
        assert result["api_key"] == "***"
        assert result["secret"] == "***"
        assert result["username"] == "testuser"  # Not sensitive
        assert result["normal_field"] == "normal_value"
    
    def test_nested_dict_filtering(self):
        """Test nested dictionary filtering"""
        input_dict = {
            "config": {
                "database": {
                    "password": "dbpassword",
                    "host": "localhost"
                },
                "api_key": "sk-test123"
            },
            "metadata": {
                "version": "1.0.0"
            }
        }
        
        result = filter_dict_sensitive_data(input_dict)
        
        assert result["config"]["database"]["password"] == "***"
        assert result["config"]["api_key"] == "***"
        assert result["config"]["database"]["host"] == "localhost"
        assert result["metadata"]["version"] == "1.0.0"
    
    def test_string_field_filtering(self):
        """Test string field filtering within dictionaries"""
        input_dict = {
            "log_message": "Error: api_key sk-1234567890 is invalid",
            "error_details": "Authorization failed with token: jwt.example",
            "safe_message": "Operation completed successfully"
        }
        
        result = filter_dict_sensitive_data(input_dict)
        
        assert "sk-***" in result["log_message"]
        assert "sk-1234567890" not in result["log_message"]
        assert "token: ***" in result["error_details"]
        assert result["safe_message"] == "Operation completed successfully"
    
    def test_case_insensitive_key_matching(self):
        """Test case-insensitive key matching"""
        input_dict = {
            "API_KEY": "sk-uppercase",
            "ApiKey": "sk-mixedcase",
            "secret_KEY": "secret123",
            "PASSWORD": "pass123"
        }
        
        result = filter_dict_sensitive_data(input_dict)
        
        # All should be filtered as keys are converted to lowercase for comparison
        for key in input_dict.keys():
            assert result[key] == "***"
    
    def test_non_dict_input(self):
        """Test handling of non-dictionary input"""
        test_inputs = ["string", 123, None, ["list", "items"]]
        
        for input_data in test_inputs:
            result = filter_dict_sensitive_data(input_data)
            assert result == input_data
    
    def test_sensitive_keys_coverage(self):
        """Test coverage of all defined sensitive keys"""
        sensitive_keys = [
            'api_key', 'apikey', 'secret', 'password', 'token', 'authorization',
            'secret_key', 'private_key', 'access_token', 'refresh_token'
        ]
        
        input_dict = {key: f"sensitive_value_{key}" for key in sensitive_keys}
        input_dict["safe_key"] = "safe_value"
        
        result = filter_dict_sensitive_data(input_dict)
        
        # All sensitive keys should be filtered
        for key in sensitive_keys:
            assert result[key] == "***", f"Key '{key}' was not filtered"
        
        # Safe key should remain unchanged
        assert result["safe_key"] == "safe_value"