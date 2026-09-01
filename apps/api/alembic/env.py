import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import Reflow models Base and settings
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from database import Base
from models.entities import (
    Content, Asset, ContentVariant, Transcript, TranscriptSegment,
    ContentBrief, GeneratedContent, Carousel, CarouselSlide, SlideElement, CarouselExport,
    Clip, ClipVariant, PlatformConnection, Publication, PostMetricSnapshot,
    PerformanceInsight, ContentPattern, ContentRecommendation, Experiment,
    ExperimentVariant, ExperimentResult, AutomationRule, AutomationExecution,
    AutomationActionExecution, GovernancePolicy, BrandProfile, QualityCheck,
    ContentClaim, GovernanceOverride, GovernanceResult, Job, SystemLog
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set database URL dynamically from Reflow settings
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite") and not db_url.startswith("sqlite+aiosqlite"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
