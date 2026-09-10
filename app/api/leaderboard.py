"""
Leaderboard API routes: retrieve ranked standings.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.leaderboard import LeaderboardResponse
from app.services.leaderboard_service import fetch_leaderboard

router = APIRouter()


@router.get("", response_model=LeaderboardResponse, summary="Get Live Leaderboard")
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns current ranked standings.
    Rank is ordered by:
    1. Game completion status DESC
    2. Levels solved DESC
    3. Effective time ASC (Elapsed time + penalties)
    """
    return await fetch_leaderboard(db)
