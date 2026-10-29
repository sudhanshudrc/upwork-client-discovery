from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_ENV = BASE_DIR / "secrets" / ".env"
ROOT_ENV = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application configuration settings."""

    # Project Metadata
    PROJECT_NAME: str = "Upwork Client Discovery & Decision-Maker Intelligence"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    BASE_DIR: Path = BASE_DIR

    # Database Configuration (PostgreSQL by default)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "upwork_leads"

    # Async database connection string for SQLAlchemy 2.0 (asyncpg)
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/upwork_leads"
    )

    # Optional sync database URL for Alembic migrations
    DATABASE_SYNC_URL: Optional[str] = (
        "postgresql://postgres:postgres@localhost:5432/upwork_leads"
    )

    # Database Connection Pool Configuration
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_PRE_PING: bool = True

    # External APIs & Authentication
    SERPAPI_API_KEY: Optional[str] = None
    UPWORK_STORAGE_STATE_PATH: Path = BASE_DIR / "secrets" / "upwork_state.json"

    # Anti-Blocking & Rate-Limiting Jitter (Seconds)
    RATE_LIMIT_MIN_JITTER_SECONDS: float = 8.0
    RATE_LIMIT_MAX_JITTER_SECONDS: float = 15.0

    # Data & Snapshot Storage Directories
    DATA_DIR: Path = BASE_DIR / "data"
    SNAPSHOTS_DIR: Path = BASE_DIR / "data" / "snapshots"
    EXPORTS_DIR: Path = BASE_DIR / "data" / "exports"
    LOGS_DIR: Path = BASE_DIR / "data" / "logs"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=(str(SECRETS_ENV), str(ROOT_ENV)),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

