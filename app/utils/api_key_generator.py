import secrets
import string
from datetime import datetime, timedelta
from typing import Optional


def generate_api_key(prefix: str = "sk", length: int = 48) -> str:
    """
    Generate a secure API key in OpenAI/Anthropic format.
    
    Args:
        prefix: Key prefix (default: "sk" like OpenAI)
        length: Total length of the random part (default: 48)
    
    Returns:
        Generated API key string
    """
    # Generate cryptographically secure random string
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return f"{prefix}-{random_part}"


def generate_openai_style_api_key() -> str:
    """Generate API key in OpenAI format (sk-...)"""
    return generate_api_key("sk", 48)


def generate_anthropic_style_api_key() -> str:
    """Generate API key in Anthropic format (sk-ant-api03-...)"""
    return generate_api_key("sk-ant-api03", 48)


def generate_expiration_date(expires_in_days: Optional[int] = None) -> Optional[datetime]:
    """
    Generate expiration date for API key.
    
    Args:
        expires_in_days: Number of days until expiration. None means no expiration.
    
    Returns:
        Expiration datetime or None if no expiration
    """
    if expires_in_days is None or expires_in_days <= 0:
        return None
    
    return datetime.now() + timedelta(days=expires_in_days)