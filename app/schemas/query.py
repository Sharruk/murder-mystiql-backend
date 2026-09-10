"""Pydantic models for Participant SQL Query execution."""

from typing import Any, List
from pydantic import BaseModel, Field


class QueryExecuteRequest(BaseModel):
    query: str = Field(..., description="SQL SELECT query to execute against investigation schema")


class QueryExecuteResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float
