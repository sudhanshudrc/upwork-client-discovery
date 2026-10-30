from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import settings
from app.models.base import Base


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

