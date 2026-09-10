"""
FastAPI dependency providers for database connections.
"""

from typing import AsyncGenerator
import asyncpg
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import connection


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session bound to the game_owner pool."""
    if connection.AsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection pool (game_owner) is not initialized.",
        )
    async with connection.AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_investigator_pool() -> asyncpg.Pool:
    """Return the raw asyncpg connection pool for investigator_ro."""
    if connection.investigator_pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Participant query engine (investigator_ro) is not initialized.",
        )
    return connection.investigator_pool
