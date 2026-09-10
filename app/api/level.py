"""
Level API routes: retrieve active level details, question, and unlocked tables.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.db.session import get_db
from app.schemas.level import LevelResponse
from app.services.game_service import get_current_level_details
from app.services.session_service import get_session_by_token

router = APIRouter()


@router.get("/current", response_model=LevelResponse, summary="Get Current Detective Level")
async def get_current_level(
    session: Session = Depends(get_session_by_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the current level question, story context, unlocked tables, attempts,
    and hint status. Never leaks the correct answer.
    """
    return await get_current_level_details(db, session)
