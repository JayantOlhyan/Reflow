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

engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True
}
if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
    })

engine = create_async_engine(db_url, **engine_kwargs)

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
    from models.entities import (
        AutomationRule, AutomationExecution, AutomationActionExecution,
        GovernancePolicy, BrandProfile, QualityCheck, ContentClaim, GovernanceOverride, GovernanceResult, Notification,
        PluginConfiguration, WebhookEndpoint, APIKey, PluginInstallation, PluginAuditLog,
        SystemJob, DeadLetterJob, Incident, IncidentEvent, SystemEvent, AlertRule, HealthHistory, WorkerHeartbeat, IdempotencyRecord
    )
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
                ("publications", "scheduled_at", "DATETIME"),
                ("publications", "timezone", "VARCHAR(64)"),
                ("publications", "claimed_at", "DATETIME"),
                ("publications", "claim_owner", "VARCHAR(64)"),
                ("publications", "cancelled_at", "DATETIME"),
                ("publications", "failed_at", "DATETIME"),
                ("publications", "analytics_status", "VARCHAR(32) DEFAULT 'NOT_SYNCED'"),
                ("publications", "last_analytics_sync_at", "DATETIME"),
                ("publications", "analytics_error_code", "VARCHAR(64)"),
                ("publications", "analytics_error_message", "TEXT"),
                ("experiments", "name", "VARCHAR(255)"),
                ("experiments", "description", "TEXT"),
                ("experiments", "scope", "VARCHAR(64)"),
                ("experiments", "platform", "VARCHAR(32)"),
                ("experiments", "started_at", "DATETIME"),
                ("experiments", "ended_at", "DATETIME"),
                ("experiments", "minimum_sample_size", "INTEGER DEFAULT 5"),
                ("experiments", "primary_metric", "VARCHAR(64) DEFAULT 'engagement_rate'"),
                ("experiments", "secondary_metrics", "TEXT DEFAULT '[]'"),
                ("experiments", "confidence_level", "FLOAT DEFAULT 0.95"),
                ("experiments", "winner_variant_id", "VARCHAR(64)"),
                ("experiments", "conclusion", "TEXT"),
                ("experiments", "created_by", "VARCHAR(64)"),
                ("experiments", "recommendation_id", "VARCHAR(64)"),
            ]
            for tbl, col, col_def in migrations:
                try:
                    await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}"))
                except Exception:
                    pass # Column already exists

            try:
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_publications_status_scheduled_at ON publications (status, scheduled_at)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_snapshots_pub_captured ON post_metric_snapshots (publication_id, captured_at)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_snapshots_platform_captured ON post_metric_snapshots (platform, captured_at)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_insights_type_scope ON performance_insights (type, scope)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_patterns_type_feature ON content_patterns (pattern_type, feature_name)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recs_type_status ON content_recommendations (type, status)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_exp_status ON experiments (status)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_variants_experiment ON experiment_variants (experiment_id)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_results_experiment ON experiment_results (experiment_id)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_experiments_recommendation ON experiments (recommendation_id)"))
                # Governance composite indexes
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_quality_checks_content_status ON quality_checks (content_id, status)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_gov_results_content ON governance_results (content_id)"))
            except Exception:
                pass

        logger.info("Database schema initialized and verified successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
