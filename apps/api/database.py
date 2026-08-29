import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings
from utils.logging import get_logger

logger = get_logger("Database")

Base = declarative_base()

# Support SQLite and PostgreSQL connection strings
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite") and not db_url.startswith("sqlite+aiosqlite"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    future=True
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """FastAPI dependency yielding an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

from sqlalchemy import text

async def init_db():
    """Initializes database schema tables and runs safe column migrations."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Safe auto-migrations for SQLite/Postgres
            migrations = [
                ("clips", "caption_style", "VARCHAR(64) DEFAULT 'BOLD_PUNCH'"),
                ("clips", "caption_enabled", "BOOLEAN DEFAULT 1"),
                ("clips", "highlight_keywords_json", "TEXT DEFAULT '[]'"),
                ("clips", "caption_custom_settings_json", "TEXT DEFAULT '{}'"),
                ("clip_variants", "has_captions", "BOOLEAN DEFAULT 0"),
                ("clip_variants", "caption_style", "VARCHAR(64)"),
                ("platform_connections", "platform", "VARCHAR(32) DEFAULT 'youtube'"),
                ("platform_connections", "account_name", "VARCHAR(128) DEFAULT ''"),
                ("platform_connections", "external_account_id", "VARCHAR(128)"),
                ("platform_connections", "status", "VARCHAR(32) DEFAULT 'CONNECTED'"),
                ("platform_connections", "access_token_encrypted", "TEXT"),
                ("platform_connections", "refresh_token_encrypted", "TEXT"),
                ("platform_connections", "token_expires_at", "DATETIME"),
                ("platform_connections", "scopes_json", "TEXT DEFAULT '[]'"),
                ("platform_connections", "metadata_json", "TEXT DEFAULT '{}'"),
            ]
            for tbl, col, col_def in migrations:
                try:
                    await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}"))
                except Exception:
                    pass # Column already exists

        logger.info("Database schema initialized and verified successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
