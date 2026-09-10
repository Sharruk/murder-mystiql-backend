"""
Service handling level hint requests and idempotent penalty application.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HintUsed, Level, Penalty, Session
from app.schemas.hint import HintRequestResponse
from app.services.session_service import get_now


async def process_hint_request(db: AsyncSession, session: Session) -> HintRequestResponse:
    """
    Reveal the current level's hint and apply the level-specific hint penalty.
    Idempotent: If the hint was already revealed for this level, returns the hint
    without applying another penalty.
    """
    now = get_now()

    if not session.current_level_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active level found for this session.",
        )

    # Fetch Level
    lvl_query = select(Level).where(Level.id == session.current_level_id)
    lvl_res = await db.execute(lvl_query)
    level = lvl_res.scalar_one_or_none()

    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Level configuration not found.",
        )

    # Check if hint already used
    hint_query = select(HintUsed).where(
        HintUsed.session_id == session.id,
        HintUsed.level_id == level.id,
    )
    hint_res = await db.execute(hint_query)
    existing_hint = hint_res.scalar_one_or_none()

    if existing_hint:
        return HintRequestResponse(
            level_order=level.order_no,
            hint_text=level.hint_text,
            penalty_applied_seconds=0,
            is_already_revealed=True,
        )

    # Apply hint usage and penalty
    hint_usage = HintUsed(
        session_id=session.id,
        level_id=level.id,
        used_at=now,
        penalty_applied_seconds=level.hint_penalty_seconds,
    )
    db.add(hint_usage)

    penalty = Penalty(
        session_id=session.id,
        reason="HINT",
        seconds=level.hint_penalty_seconds,
        applied_at=now,
    )
    db.add(penalty)

    await db.commit()

    return HintRequestResponse(
        level_order=level.order_no,
        hint_text=level.hint_text,
        penalty_applied_seconds=level.hint_penalty_seconds,
        is_already_revealed=False,
    )
