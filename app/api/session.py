"""
Session API routes: lookup participant username, create/resume game session.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.session import SessionStartRequest, SessionStartResponse
from app.services.session_service import start_or_resume_session

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse, summary="Start or Resume Detective Session")
async def start_session(
    payload: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a pre-assigned username (e.g. DETECTIVE-01).
    - Verifies username exists in the participants table.
    - Creates a new session if none exists.
    - Resumes existing session if already started.
    - Returns an opaque session token, current level order, lock status, and effective time.
    """
    return await start_or_resume_session(db, payload.username, payload.pin)
