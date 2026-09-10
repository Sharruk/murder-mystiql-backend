"""Pydantic models for Hints."""

from pydantic import BaseModel, Field


class HintRequestResponse(BaseModel):
    level_order: int
    hint_text: str
    penalty_applied_seconds: int
    is_already_revealed: bool = Field(
        ..., description="True if hint was previously unlocked (penalty not charged again)"
    )
