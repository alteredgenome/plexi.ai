import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Plexi"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./plexi.db"
    
    # OpenRouter / LLM
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "google/gemma-2-9b-it:free"
    
    # Home Assistant
    HOME_ASSISTANT_URL: Optional[str] = "http://homeassistant.local:8123"
    HOME_ASSISTANT_TOKEN: Optional[str] = None
    
    # Pavlok
    PAVLOK_API_KEY: Optional[str] = None
    
    # Security - dynamically generated fallback secret
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Setup state
    SETUP_COMPLETED: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
