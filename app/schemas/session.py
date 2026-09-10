"""Pydantic models for Session management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    username: str = Field(..., description="Pre-assigned detective username (e.g. DETECTIVE-01)")
    pin: Optional[str] = Field(None, description="Optional team PIN if enabled")


class ParticipantInfo(BaseModel):
    id: int
    username: str
    display_name: str
    seat_no: Optional[str] = None


class SessionStartResponse(BaseModel):
    token: str = Field(..., description="Opaque session token to be passed in Authorization or X-Session-Token")
    participant: ParticipantInfo
    current_level_order: int
    is_locked: bool
    remaining_lock_seconds: int
    effective_time_seconds: int
    is_completed: bool
