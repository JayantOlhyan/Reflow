import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Reflow API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./reflow.db")
    
    # Storage
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")  # local, s3, r2
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
    STORAGE_BUCKET: Optional[str] = os.getenv("STORAGE_BUCKET", None)
    
    # AI Providers
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)
    
    # Redis Queue
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Platform App OAuth Credentials
    YOUTUBE_CLIENT_ID: Optional[str] = os.getenv("YOUTUBE_CLIENT_ID", None)
    YOUTUBE_CLIENT_SECRET: Optional[str] = os.getenv("YOUTUBE_CLIENT_SECRET", None)
    META_CLIENT_ID: Optional[str] = os.getenv("META_CLIENT_ID", None)
    META_CLIENT_SECRET: Optional[str] = os.getenv("META_CLIENT_SECRET", None)
    TIKTOK_CLIENT_KEY: Optional[str] = os.getenv("TIKTOK_CLIENT_KEY", None)
    TIKTOK_CLIENT_SECRET: Optional[str] = os.getenv("TIKTOK_CLIENT_SECRET", None)
    LINKEDIN_CLIENT_ID: Optional[str] = os.getenv("LINKEDIN_CLIENT_ID", None)
    LINKEDIN_CLIENT_SECRET: Optional[str] = os.getenv("LINKEDIN_CLIENT_SECRET", None)
    X_CLIENT_ID: Optional[str] = os.getenv("X_CLIENT_ID", None)
    X_CLIENT_SECRET: Optional[str] = os.getenv("X_CLIENT_SECRET", None)

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
