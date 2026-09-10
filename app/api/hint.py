"""
Hint API routes: request hint for active level and apply configured penalty.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.db.session import get_db
from app.schemas.hint import HintRequestResponse
from app.services.hint_service import process_hint_request
from app.services.leaderboard_service import broadcast_leaderboard_update
from app.services.session_service import get_session_by_token

router = APIRouter()


@router.post("/request", response_model=HintRequestResponse, summary="Request Level Hint")
async def request_hint(
    session: Session = Depends(get_session_by_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the hint for the current level.
    - Applies the level's configured hint penalty in seconds.
    - Idempotent: If already used for this level, returns the hint without charging penalty again.
    - Triggers real-time leaderboard update via WebSocket.
    """
    response = await process_hint_request(db, session)
    if not response.is_already_revealed:
        await broadcast_leaderboard_update(db)
    return response
