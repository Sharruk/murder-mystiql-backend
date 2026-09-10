"""
Service managing level retrieval, progress, and unlock metadata.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HintUsed, Level, LevelProgress, Session
from app.schemas.level import LevelResponse
from app.services.session_service import calculate_session_lock


async def get_current_level_details(db: AsyncSession, session: Session) -> LevelResponse:
    """
    Retrieve the participant's current level without exposing answers or future levels.
    """
    if not session.current_level_id:
        # Check if game is completed
        if session.completed_at:
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Congratulations! You have completed all levels in MurderMystiQL.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current level not set for this session.",
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

    # Check Hint Status
    hint_query = select(HintUsed).where(
        HintUsed.session_id == session.id,
        HintUsed.level_id == level.id,
    )
    hint_res = await db.execute(hint_query)
    hint_record = hint_res.scalar_one_or_none()
    is_hint_used = hint_record is not None
    revealed_hint = level.hint_text if is_hint_used else None

    # Check Level Progress Attempts
    prog_query = select(LevelProgress).where(
        LevelProgress.session_id == session.id,
        LevelProgress.level_id == level.id,
    )
    prog_res = await db.execute(prog_query)
    progress = prog_res.scalar_one_or_none()
    attempts = progress.attempts if progress else 0

    # Calculate Lock
    is_locked, remaining_lock = calculate_session_lock(session)

    # Convert unlocks_tables if stored as list/JSON
    unlocks = level.unlocks_tables if isinstance(level.unlocks_tables, list) else []

    return LevelResponse(
        id=level.id,
        order_no=level.order_no,
        title=level.title,
        story_context=level.story_context,
        question_text=level.question_text,
        unlocks_tables=unlocks,
        attempts=attempts,
        is_hint_used=is_hint_used,
        hint_text=revealed_hint,
        hint_penalty_seconds=level.hint_penalty_seconds,
        is_locked=is_locked,
        remaining_lock_seconds=remaining_lock,
    )
