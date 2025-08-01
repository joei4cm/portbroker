from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_type: str = "sqlite"
    database_url: str = "sqlite:///./portbroker.db"
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    default_openai_api_key: Optional[str] = None
    default_openai_base_url: str = "https://api.openai.com/v1"
    default_big_model: str = "gpt-4o"
    default_small_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"


settings = Settings()