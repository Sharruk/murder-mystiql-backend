"""Pydantic models for Level data."""

from typing import List, Optional
from pydantic import BaseModel, Field


class LevelResponse(BaseModel):
    id: int
    order_no: int
    title: str
    story_context: str
    question_text: str
    unlocks_tables: List[str]
    attempts: int
    is_hint_used: bool
    hint_text: Optional[str] = Field(None, description="Only populated if hint has been requested")
    hint_penalty_seconds: int
    is_locked: bool
    remaining_lock_seconds: int
