"""
Service handling participant session creation, resumption, and token resolution.
"""

import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import generate_session_token
from app.db.models import Level, LevelProgress, Participant, Penalty, Session
from app.db.session import get_db
from app.schemas.session import ParticipantInfo, SessionStartResponse


def get_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_session_lock(session: Session) -> Tuple[bool, int]:
    """Check whether a session is currently in a submission lock period."""
    if not session.locked_until:
        return False, 0
    now = get_now()
    locked_until = ensure_utc(session.locked_until)
    if locked_until and locked_until > now:
        remaining = int((locked_until - now).total_seconds())
        return True, max(0, remaining)
    return False, 0


async def calculate_effective_time(db: AsyncSession, session: Session) -> int:
    """
    Calculate effective time in seconds:
    (Completed_at or NOW() - Started_at) + sum of all penalty seconds.
    """
    now = get_now()
    end_time = ensure_utc(session.completed_at) if session.completed_at else now
    started_at = ensure_utc(session.started_at)
    elapsed_seconds = max(0, int((end_time - started_at).total_seconds()))

    penalty_query = select(func.coalesce(func.sum(Penalty.seconds), 0)).where(
        Penalty.session_id == session.id
    )
    res = await db.execute(penalty_query)
    total_penalty = res.scalar_one_or_none() or 0

    return elapsed_seconds + int(total_penalty)


async def start_or_resume_session(
    db: AsyncSession, username: str, pin: Optional[str] = None
) -> SessionStartResponse:
    """
    Start a new session or resume an existing session for a pre-assigned username.
    """
    clean_username = username.strip().upper()

    # 1. Lookup Participant
    query = select(Participant).where(Participant.username == clean_username)
    result = await db.execute(query)
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant username '{username}' not found. Please verify your assigned detective ID.",
        )

    # If PIN verification is configured on participant, it must be supplied and match exactly.
    # Constant-time comparison avoids leaking correctness via response-time differences.
    if participant.pin and not secrets.compare_digest(participant.pin, pin or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN for this detective account.",
        )

    # 2. Check for existing session
    sess_query = (
        select(Session)
        .where(Session.participant_id == participant.id)
        .options(selectinload(Session.current_level))
    )
    sess_res = await db.execute(sess_query)
    session = sess_res.scalar_one_or_none()

    if not session:
        # Create new session starting at Level 1
        level_query = select(Level).order_by(Level.order_no.asc()).limit(1)
        lvl_res = await db.execute(level_query)
        first_level = lvl_res.scalar_one_or_none()

        if not first_level:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Game levels are not configured in the database.",
            )

        token = generate_session_token()
        session = Session(
            participant_id=participant.id,
            token=token,
            current_level_id=first_level.id,
            started_at=get_now(),
        )
        db.add(session)
        await db.flush()

        # Create Level 1 progress
        progress = LevelProgress(
            session_id=session.id,
            level_id=first_level.id,
            unlocked_at=session.started_at,
            attempts=0,
        )
        db.add(progress)
        await db.commit()
        await db.refresh(session)
        session.current_level = first_level

    # Calculate current state
    is_locked, remaining_lock = calculate_session_lock(session)
    effective_time = await calculate_effective_time(db, session)
    current_level_order = session.current_level.order_no if session.current_level else 1
    is_completed = session.completed_at is not None

    return SessionStartResponse(
        token=session.token,
        participant=ParticipantInfo(
            id=participant.id,
            username=participant.username,
            display_name=participant.display_name,
            seat_no=participant.seat_no,
        ),
        current_level_order=current_level_order,
        is_locked=is_locked,
        remaining_lock_seconds=remaining_lock,
        effective_time_seconds=effective_time,
        is_completed=is_completed,
    )


async def get_session_by_token(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
) -> Session:
    """
    Authenticate and extract session from Authorization Bearer header or X-Session-Token.
    """
    token: Optional[str] = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        elif len(parts) == 1:
            token = parts[0]
    elif x_session_token:
        token = x_session_token.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token missing. Provide via 'Authorization: Bearer <token>' or 'X-Session-Token: <token>'.",
        )

    query = (
        select(Session)
        .where(Session.token == token)
        .options(
            selectinload(Session.participant),
            selectinload(Session.current_level),
        )
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )

    return session
