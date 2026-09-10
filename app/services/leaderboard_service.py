"""
Service for computing leaderboard standings and broadcasting live updates over WebSockets.
"""

from typing import List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Level, LevelProgress, Participant, Penalty, Session
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from app.services.session_service import ensure_utc, get_now
from app.websocket.leaderboard import ws_manager


async def fetch_leaderboard(db: AsyncSession) -> LeaderboardResponse:
    """
    Computes current standings across all active and completed sessions.
    Sorts by:
    1. Completion status DESC
    2. Levels solved DESC
    3. Effective time ASC
    """
    now = get_now()

    # Query all sessions with participants, levels, progress, and penalties
    query = (
        select(Session)
        .join(Participant, Session.participant_id == Participant.id)
        .options(
            selectinload(Session.participant),
            selectinload(Session.current_level),
            selectinload(Session.level_progress),
            selectinload(Session.penalties),
        )
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    raw_entries = []
    for s in sessions:
        end_time = ensure_utc(s.completed_at) if s.completed_at else now
        started_at = ensure_utc(s.started_at)
        elapsed_seconds = max(0, int((end_time - started_at).total_seconds()))

        # Calculate penalties
        total_penalties = sum(p.seconds for p in s.penalties)
        wrong_count = sum(1 for p in s.penalties if p.reason == "WRONG_ANSWER")
        hints_count = sum(1 for p in s.penalties if p.reason == "HINT")

        effective_time = elapsed_seconds + total_penalties

        # Count solved levels
        solved_count = sum(1 for prog in s.level_progress if prog.solved_at is not None)
        current_lvl_order = s.current_level.order_no if s.current_level else 1
        is_completed = s.completed_at is not None

        raw_entries.append({
            "username": s.participant.username,
            "display_name": s.participant.display_name,
            "seat_no": s.participant.seat_no,
            "current_level_order": current_lvl_order,
            "levels_solved": solved_count,
            "total_penalty_seconds": total_penalties,
            "wrong_answers_count": wrong_count,
            "hints_used_count": hints_count,
            "effective_time_seconds": effective_time,
            "is_completed": is_completed,
        })

    # Sort
    raw_entries.sort(
        key=lambda x: (
            not x["is_completed"],  # Completed first (False < True)
            -x["levels_solved"],    # More levels solved first
            x["effective_time_seconds"],  # Lower effective time first
        )
    )

    # Assign ranks
    entries: List[LeaderboardEntry] = []
    current_rank = 1
    for idx, item in enumerate(raw_entries):
        if idx > 0:
            prev = raw_entries[idx - 1]
            # Check if tied
            is_tied = (
                item["is_completed"] == prev["is_completed"]
                and item["levels_solved"] == prev["levels_solved"]
                and item["effective_time_seconds"] == prev["effective_time_seconds"]
            )
            if not is_tied:
                current_rank = idx + 1

        entries.append(LeaderboardEntry(rank=current_rank, **item))

    return LeaderboardResponse(
        entries=entries,
        total_participants=len(entries),
        generated_at=now,
    )


async def broadcast_leaderboard_update(db: AsyncSession):
    """Fetch the latest leaderboard and broadcast it to all connected WebSocket clients."""
    try:
        lb = await fetch_leaderboard(db)
        await ws_manager.broadcast({
            "event": "LEADERBOARD_UPDATE",
            "data": lb.model_dump(mode="json"),
        })
    except Exception as exc:
        print(f"[ERROR] Failed to broadcast leaderboard: {exc}")
