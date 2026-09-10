"""Pydantic models for Answer Submissions."""

from typing import Optional
from pydantic import BaseModel, Field


class AnswerSubmitRequest(BaseModel):
    answer: str = Field(..., description="The answer to the current level question")


class AnswerSubmitResponse(BaseModel):
    is_correct: bool
    message: str
    completed: bool
    next_level_order: Optional[int] = None
    is_locked: bool = False
    remaining_lock_seconds: int = 0
    penalty_applied_seconds: int = 0
