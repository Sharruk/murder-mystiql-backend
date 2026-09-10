"""
Service for answer submission, validation, penalty assignment, and level advancement.
"""

from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Level, LevelProgress, Penalty, Session, Submission
from app.schemas.answer import AnswerSubmitResponse
from app.services.session_service import calculate_session_lock, get_now


async def process_answer_submission(
    db: AsyncSession, session: Session, submitted_answer: str
) -> AnswerSubmitResponse:
    """
    Validates participant answer submission.
    Applies 1-minute lock and 5-minute penalty on wrong answer.
    Unlocks next level on correct answer.
    """
    now = get_now()

    # 1. Check if session is currently locked
    is_locked, remaining_lock = calculate_session_lock(session)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Submissions are locked for another {remaining_lock} seconds due to a previous incorrect attempt.",
        )

    # 2. Check if participant already completed the game
    if session.completed_at:
        return AnswerSubmitResponse(
            is_correct=True,
            message="You have already completed all investigation levels!",
            completed=True,
            next_level_order=None,
            is_locked=False,
            remaining_lock_seconds=0,
            penalty_applied_seconds=0,
        )

    # 3. Fetch current level
    lvl_query = select(Level).where(Level.id == session.current_level_id)
    lvl_res = await db.execute(lvl_query)
    current_level = lvl_res.scalar_one_or_none()

    if not current_level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current level not found.",
        )

    # 4. Fetch level progress record
    prog_query = select(LevelProgress).where(
        LevelProgress.session_id == session.id,
        LevelProgress.level_id == current_level.id,
    )
    prog_res = await db.execute(prog_query)
    progress = prog_res.scalar_one_or_none()
    if not progress:
        progress = LevelProgress(
            session_id=session.id,
            level_id=current_level.id,
            unlocked_at=now,
            attempts=0,
        )
        db.add(progress)

    progress.attempts += 1

    # 5. Evaluate answer (trimmed, case-insensitive)
    clean_submission = submitted_answer.strip()
    clean_expected = current_level.correct_answer.strip()
    is_correct = clean_submission.lower() == clean_expected.lower()

    # Record submission audit
    submission_record = Submission(
        session_id=session.id,
        level_id=current_level.id,
        submitted_answer=clean_submission,
        is_correct=is_correct,
        submitted_at=now,
    )
    db.add(submission_record)

    if is_correct:
        # Correct answer
        progress.solved_at = now

        # Find next level
        next_lvl_query = (
            select(Level)
            .where(Level.order_no > current_level.order_no)
            .order_by(Level.order_no.asc())
            .limit(1)
        )
        next_lvl_res = await db.execute(next_lvl_query)
        next_level = next_lvl_res.scalar_one_or_none()

        if next_level:
            session.current_level_id = next_level.id
            # Create next level progress
            next_prog = LevelProgress(
                session_id=session.id,
                level_id=next_level.id,
                unlocked_at=now,
                attempts=0,
            )
            db.add(next_prog)
            await db.commit()
            return AnswerSubmitResponse(
                is_correct=True,
                message=f"Brilliant detective work! Level {current_level.order_no} solved.",
                completed=False,
                next_level_order=next_level.order_no,
                is_locked=False,
                remaining_lock_seconds=0,
                penalty_applied_seconds=0,
            )
        else:
            # Final level solved!
            session.completed_at = now
            await db.commit()
            return AnswerSubmitResponse(
                is_correct=True,
                message="Case Closed! You have solved all levels and unmasked the culprit.",
                completed=True,
                next_level_order=None,
                is_locked=False,
                remaining_lock_seconds=0,
                penalty_applied_seconds=0,
            )

    else:
        # Incorrect answer
        # Apply 1-minute submission lock
        lock_until = now + timedelta(seconds=settings.WRONG_ANSWER_LOCK_SECONDS)
        session.locked_until = lock_until

        # Apply 5-minute time penalty (300 seconds)
        penalty = Penalty(
            session_id=session.id,
            reason="WRONG_ANSWER",
            seconds=settings.WRONG_ANSWER_PENALTY_SECONDS,
            applied_at=now,
        )
        db.add(penalty)
        await db.commit()

        return AnswerSubmitResponse(
            is_correct=False,
            message="Incorrect answer. A 1-minute submission lock and 5-minute time penalty have been applied.",
            completed=False,
            next_level_order=None,
            is_locked=True,
            remaining_lock_seconds=settings.WRONG_ANSWER_LOCK_SECONDS,
            penalty_applied_seconds=settings.WRONG_ANSWER_PENALTY_SECONDS,
        )
