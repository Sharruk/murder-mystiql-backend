"""Pydantic models for Leaderboard."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    display_name: str
    seat_no: Optional[str] = None
    current_level_order: int
    levels_solved: int
    total_penalty_seconds: int
    wrong_answers_count: int
    hints_used_count: int
    effective_time_seconds: int
    is_completed: bool


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    total_participants: int
    generated_at: datetime
