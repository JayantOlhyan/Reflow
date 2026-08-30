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
    
    # Security & Credential Encryption
    ENCRYPTION_SECRET: str = Field(
        default="reflow_dev_secret_key_change_in_production_32b",
        description="Master server key used to encrypt OAuth tokens at rest"
    )

    # Platform App OAuth Credentials (Configured by self-hosted admin)
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None
    YOUTUBE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/youtube/callback",
        description="OAuth 2.0 callback redirect URI for Google/YouTube"
    )
    YOUTUBE_SCOPES: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/userinfo.profile"
        ]
    )

    # Meta (Instagram & Facebook)
    META_CLIENT_ID: Optional[str] = None
    META_CLIENT_SECRET: Optional[str] = None
    INSTAGRAM_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/instagram/callback",
        description="OAuth 2.0 callback redirect URI for Instagram"
    )
    INSTAGRAM_SCOPES: List[str] = Field(
        default=[
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "pages_read_engagement"
        ]
    )
    FACEBOOK_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/facebook/callback",
        description="OAuth 2.0 callback redirect URI for Facebook Pages"
    )
    FACEBOOK_SCOPES: List[str] = Field(
        default=[
            "pages_manage_posts",
            "pages_read_engagement",
            "pages_show_list",
            "publish_video"
        ]
    )

    # LinkedIn
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/linkedin/callback",
        description="OAuth 2.0 callback redirect URI for LinkedIn"
    )
    LINKEDIN_SCOPES: List[str] = Field(
        default=[
            "openid",
            "profile",
            "email",
            "w_member_social"
        ]
    )

    # X / Twitter
    X_CLIENT_ID: Optional[str] = None
    X_CLIENT_SECRET: Optional[str] = None
    X_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/x/callback",
        description="OAuth 2.0 callback redirect URI for X (Twitter)"
    )
    X_SCOPES: List[str] = Field(
        default=[
            "tweet.read",
            "tweet.write",
            "users.read",
            "offline.access"
        ]
    )

    # TikTok
    TIKTOK_CLIENT_KEY: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None
    TIKTOK_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/tiktok/callback",
        description="OAuth 2.0 callback redirect URI for TikTok"
    )
    TIKTOK_SCOPES: List[str] = Field(
        default=["user.info.basic", "video.upload", "video.publish"]
    )

    # Pinterest
    PINTEREST_APP_ID: Optional[str] = None
    PINTEREST_APP_SECRET: Optional[str] = None
    PINTEREST_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/pinterest/callback"
    )

    # Threads
    THREADS_APP_ID: Optional[str] = None
    THREADS_APP_SECRET: Optional[str] = None
    THREADS_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/connections/threads/callback"
    )

    # Phase 9: Scheduler Engine Configuration
    SCHEDULER_MIN_LEAD_SECONDS: int = Field(
        default=60,
        description="Minimum seconds required between current time and scheduled time"
    )
    SCHEDULER_POLL_INTERVAL_SECONDS: float = Field(
        default=5.0,
        description="Tick frequency in seconds for scheduler daemon to claim due publications"
    )
    SCHEDULER_CLAIM_LEASE_SECONDS: int = Field(
        default=120,
        description="Lease timeout before a claimed publication is considered stale and recovered"
    )
    SCHEDULER_MISSED_POLICY: str = Field(
        default="EXECUTE_IMMEDIATELY",
        description="Policy for missed publications on recovery: 'EXECUTE_IMMEDIATELY' | 'MARK_FAILED'"
    )

    # Phase 10: Analytics & Performance Intelligence Configuration
    ANALYTICS_SYNC_INTERVAL_MINUTES: int = Field(
        default=60,
        description="Interval in minutes for scheduler to sweep and queue metrics sync for active publications"
    )
    ANALYTICS_STALE_AFTER_HOURS: int = Field(
        default=24,
        description="Hours after which an analytics snapshot is marked stale in UI"
    )
    MIN_ANALYTICS_SAMPLE_SIZE: int = Field(
        default=50,
        description="Minimum views/impressions threshold before declaring top-performing rank"
    )
    ANALYTICS_REFRESH_COOLDOWN_SECONDS: int = Field(
        default=60,
        description="Cooldown in seconds between manual user-initiated analytics refresh requests"
    )

    # Phase 11: Content Intelligence & Recommendation Configuration
    MIN_RECOMMENDATION_SAMPLES: int = Field(
        default=5,
        description="Minimum publication samples required to produce account-specific recommendations"
    )
    INTELLIGENCE_STALE_AFTER_HOURS: int = Field(
        default=24,
        description="Hours after which intelligence insights are considered stale"
    )
    OUTLIER_TRIM_PERCENTILE: float = Field(
        default=0.05,
        description="Fraction of top and bottom performance distribution to trim for robust baseline calculation"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure local storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
