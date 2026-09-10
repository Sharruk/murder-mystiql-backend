"""Pydantic models for Proctoring & Violations."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProctorViolationRequest(BaseModel):
    type: str = Field(..., description="Type of violation (e.g. TAB_SWITCH, FULLSCREEN_EXIT, BLUR)")
    detail: Optional[str] = Field(None, description="Optional metadata or client context")


class ProctorViolationResponse(BaseModel):
    status: str
    violation_id: int
    recorded_at: datetime
