"""
Answer API routes: submit answer, advance level, apply lock and penalties.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.db.session import get_db
from app.schemas.answer import AnswerSubmitRequest, AnswerSubmitResponse
from app.services.leaderboard_service import broadcast_leaderboard_update
from app.services.scoring_service import process_answer_submission
from app.services.session_service import get_session_by_token

router = APIRouter()


@router.post("/submit", response_model=AnswerSubmitResponse, summary="Submit Level Answer")
async def submit_answer(
    payload: AnswerSubmitRequest,
    session: Session = Depends(get_session_by_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates participant's answer against the backend correct answer.
    - If correct: Unlocks the next level or marks completion.
    - If incorrect: Applies 1-minute submission lock and 5-minute time penalty.
    - Triggers real-time leaderboard update via WebSocket.
    """
    response = await process_answer_submission(db, session, payload.answer)
    # Broadcast updated standings
    await broadcast_leaderboard_update(db)
    return response
