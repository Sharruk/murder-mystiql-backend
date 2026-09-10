"""
Service for recording and tracking proctoring events and violations.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProctorViolation, Session
from app.schemas.proctor import ProctorViolationResponse
from app.services.session_service import get_now


async def record_proctor_violation(
    db: AsyncSession, session: Session, violation_type: str, detail: Optional[str] = None
) -> ProctorViolationResponse:
    """Record a browser/client proctor event (tab switch, blur, fullscreen exit)."""
    now = get_now()
    violation = ProctorViolation(
        session_id=session.id,
        type=violation_type.strip().upper(),
        detail=detail,
        occurred_at=now,
    )
    db.add(violation)
    await db.commit()
    await db.refresh(violation)

    return ProctorViolationResponse(
        status="recorded",
        violation_id=violation.id,
        recorded_at=violation.occurred_at,
    )
