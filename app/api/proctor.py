"""
Proctor API routes: log browser violations (tab switch, blur, fullscreen exit).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.db.session import get_db
from app.schemas.proctor import ProctorViolationRequest, ProctorViolationResponse
from app.services.proctor_service import record_proctor_violation
from app.services.session_service import get_session_by_token

router = APIRouter()


@router.post("/violation", response_model=ProctorViolationResponse, summary="Record Proctor Violation")
async def log_violation(
    payload: ProctorViolationRequest,
    session: Session = Depends(get_session_by_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Records a participant browser event (e.g. TAB_SWITCH, FULLSCREEN_EXIT, FOCUS_LOSS).
    """
    return await record_proctor_violation(db, session, payload.type, payload.detail)
