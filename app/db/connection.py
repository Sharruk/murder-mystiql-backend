"""
Database connection management.
Maintains two separate connection pools:
1. game_engine & AsyncSessionLocal: SQLAlchemy async session pool for 'game_owner'.
2. investigator_pool: asyncpg Pool for strictly read-only 'investigator_ro' participant queries.
"""

from typing import Optional
import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Pool 1: game_owner (SQLAlchemy Async Engine)
game_engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None

# Pool 2: investigator_ro (asyncpg Pool)
investigator_pool: Optional[asyncpg.Pool] = None


async def init_db() -> None:
    """Initialize both database connection pools."""
    global game_engine, AsyncSessionLocal, investigator_pool

    # Initialize Pool 1: game_owner
    game_engine = create_async_engine(
        settings.GAME_DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=game_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Initialize Pool 2: investigator_ro
    # Only initialize asyncpg if URL starts with postgresql
    if settings.INVESTIGATOR_DATABASE_URL.startswith("postgresql"):
        # Convert any postgresql+asyncpg:// to postgresql:// for asyncpg direct driver
        dsn = settings.INVESTIGATOR_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        try:
            investigator_pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=settings.INVESTIGATOR_POOL_MIN_SIZE,
                max_size=settings.INVESTIGATOR_POOL_MAX_SIZE,
                command_timeout=settings.STATEMENT_TIMEOUT_MS / 1000.0,
                server_settings={
                    "default_transaction_read_only": "on",
                    "statement_timeout": f"{settings.STATEMENT_TIMEOUT_MS}",
                },
            )
        except Exception as e:
            # When running unit tests without a running live PostgreSQL server, log warning
            print(f"[WARNING] Could not initialize investigator_ro asyncpg pool: {e}")
            investigator_pool = None


async def close_db() -> None:
    """Close both database connection pools gracefully."""
    global game_engine, investigator_pool

    if investigator_pool is not None:
        await investigator_pool.close()
        investigator_pool = None

    if game_engine is not None:
        await game_engine.dispose()
        game_engine = None
