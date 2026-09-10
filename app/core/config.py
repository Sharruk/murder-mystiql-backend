"""
Application configuration management using pydantic-settings.
Reads configuration from environment variables and .env file.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "MurderMystiQL Backend"
    APP_ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Session Security
    SESSION_SECRET: str = "dev-offline-secret-key-change-in-production"

    # Database URLs
    # POOL 1: game_owner connection (Read/Write to 'game' schema)
    GAME_DATABASE_URL: str = Field(
        default="postgresql+asyncpg://game_owner:GameOwnerSecurePass123!@localhost:5432/murdermystiql",
        description="Async SQLAlchemy database URL for game_owner role",
    )

    # POOL 2: investigator_ro connection (Strictly Read-Only to 'investigation' schema)
    INVESTIGATOR_DATABASE_URL: str = Field(
        default="postgresql://investigator_ro:InvestigatorReadOnlyPass123!@localhost:5432/murdermystiql",
        description="asyncpg database URL for investigator_ro role",
    )

    # Participant SQL Safety Constraints
    STATEMENT_TIMEOUT_MS: int = 5000
    MAX_QUERY_ROWS: int = 500
    INVESTIGATOR_POOL_MIN_SIZE: int = 5
    INVESTIGATOR_POOL_MAX_SIZE: int = 10

    # Game Rule Penalties & Durations (in seconds)
    WRONG_ANSWER_LOCK_SECONDS: int = 60
    WRONG_ANSWER_PENALTY_SECONDS: int = 300

    # Static Frontend Path (optional: built React frontend for offline LAN serving)
    FRONTEND_DIST_DIR: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
