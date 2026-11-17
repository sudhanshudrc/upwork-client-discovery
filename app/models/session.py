from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import settings
from app.models.base import Base
from sqlalchemy.pool import NullPool


# Determine pool arguments depending on dialect (PostgreSQL vs SQLite)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "echo": settings.DEBUG,
}

if not is_sqlite:
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_pre_ping": settings.DB_POOL_PRE_PING,
        }
    )

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)
async_engine: AsyncEngine = engine

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Dedicated task engine for background workers (Celery) with NullPool to prevent
# asyncpg connection pooling across multiple event loops and task executions.
task_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=settings.DEBUG,
)

TaskAsyncSessionLocal = async_sessionmaker(
    bind=task_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

from contextlib import asynccontextmanager


@asynccontextmanager
async def get_task_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    On-demand async session context manager for Celery background tasks.
    Creates a fresh, completely unpooled AsyncEngine with NullPool bound strictly
    to the current active event loop, and disposes it completely on exit.
    Prevents cross-event-loop connection sharing and process fork inheritance.
    """
    task_eng = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=settings.DEBUG,
    )
    session_factory = async_sessionmaker(
        bind=task_eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await task_eng.dispose()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency: Yields an async database session with automatic commit / rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Creates database tables if they do not exist and synchronizes missing columns."""
    from sqlalchemy import text
    import app.models  # noqa: F401 - Register all models with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Apply schema column synchronizations for existing deployments
        if not is_sqlite:
            await conn.execute(
                text(
                    "ALTER TABLE search_runs ADD COLUMN IF NOT EXISTS raw_jobs_payload JSON;"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE search_runs ADD COLUMN IF NOT EXISTS is_cached_hit BOOLEAN NOT NULL DEFAULT FALSE;"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_search_runs_query_created ON search_runs (search_query, created_at);"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id);"
                )
            )
            # Synchronize scheduled_keyword_searches columns
            await conn.execute(
                text(
                    "ALTER TABLE scheduled_keyword_searches ADD COLUMN IF NOT EXISTS execution_time VARCHAR(10) DEFAULT '10:30' NOT NULL;"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE scheduled_keyword_searches ADD COLUMN IF NOT EXISTS selected_days JSON DEFAULT '[]' NOT NULL;"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE scheduled_keyword_searches ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Asia/Kolkata' NOT NULL;"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE scheduled_keyword_searches ADD COLUMN IF NOT EXISTS min_delay_seconds FLOAT DEFAULT 30.0 NOT NULL;"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE scheduled_keyword_searches ADD COLUMN IF NOT EXISTS max_delay_seconds FLOAT DEFAULT 120.0 NOT NULL;"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE scheduled_keyword_searches ALTER COLUMN interval_hours DROP NOT NULL;"
                )
            )
            # Remove any existing session cookies for requested test resets
            await conn.execute(
                text(
                    "DELETE FROM user_sessions WHERE user_identifier = 'sudhanshushekarkumar@gmail.com' OR user_id IN (SELECT id FROM users WHERE email = 'sudhanshushekarkumar@gmail.com');"
                )
            )

