import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "Reflow API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="development | production | test")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "*"]
    )
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./storage/reflow.db",
        description="Database connection URL (SQLite or PostgreSQL)"
    )
    
    # Storage & Upload Limits
    STORAGE_PROVIDER: str = Field(default="local", description="local | s3 | r2")
    STORAGE_DIR: str = Field(default="./storage", description="Base directory for local file storage")
    STORAGE_BUCKET: Optional[str] = None
    STORAGE_ACCESS_KEY: Optional[str] = None
    STORAGE_SECRET_KEY: Optional[str] = None
    MAX_UPLOAD_SIZE_MB: int = Field(default=500, description="Max upload size in Megabytes")
    
    # Queue / Cache (Redis)
    REDIS_URL: Optional[str] = Field(default="redis://localhost:6379/0")
    REDIS_MEDIA_QUEUE: str = Field(default="reflow:media_jobs")
    
    # Media Processing Engine Configuration
    MAX_MEDIA_RETRIES: int = Field(default=3, description="Maximum retry attempts for failed media processing")
    MEDIA_WORKER_CONCURRENCY: int = Field(default=1, description="Number of concurrent media worker tasks")
    FFMPEG_PATH: str = Field(default="ffmpeg", description="Path to ffmpeg binary")
    FFPROBE_PATH: str = Field(default="ffprobe", description="Path to ffprobe binary")
    
    # AI Providers (Bring Your Own Key)
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Platform App OAuth Credentials (Configured by self-hosted admin)
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None
    META_CLIENT_ID: Optional[str] = None
    META_CLIENT_SECRET: Optional[str] = None
    TIKTOK_CLIENT_KEY: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    X_CLIENT_ID: Optional[str] = None
    X_CLIENT_SECRET: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure local storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
