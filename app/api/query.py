"""
Query API routes: execute participant SQL query via investigator_ro.
"""

import asyncpg
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.db.session import get_db, get_investigator_pool
from app.schemas.query import QueryExecuteRequest, QueryExecuteResponse
from app.services.query_service import execute_participant_sql
from app.services.session_service import get_session_by_token

router = APIRouter()


@router.post("/execute", response_model=QueryExecuteResponse, summary="Execute Participant SQL Query")
async def execute_query(
    payload: QueryExecuteRequest,
    session: Session = Depends(get_session_by_token),
    pool: asyncpg.Pool = Depends(get_investigator_pool),
):
    """
    Executes a participant SQL query against the investigation schema.
    - Uses strictly the investigator_ro pool.
    - SET TRANSACTION READ ONLY.
    - 5-second statement timeout.
    - Max 500 rows limit.
    - Rejects multi-statements, DDL, DML writes, and access to internal schemas.
    """
    return await execute_participant_sql(pool, payload.query)
