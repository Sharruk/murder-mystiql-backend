"""
Participant SQL Query Execution Service.
Enforces security sandboxing, transaction read-only mode, statement timeout,
and row count caps using the investigator_ro pool.
"""

import time
from typing import Any, List
import asyncpg
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import validate_participant_sql
from app.schemas.query import QueryExecuteResponse


def sanitize_cell_value(val: Any) -> Any:
    """Ensure all returned cell values are JSON serializable."""
    if val is None:
        return None
    if isinstance(val, (int, float, bool, str)):
        return val
    return str(val)


async def execute_participant_sql(pool: asyncpg.Pool, raw_query: str) -> QueryExecuteResponse:
    """
    Executes participant SQL against the investigation schema via investigator_ro.
    Enforces:
    - Pre-execution validation & security inspection.
    - Read-only transaction.
    - 5-second statement timeout.
    - Max 500 rows returned.
    """
    # 1. Pre-execution security and statement validation
    try:
        sanitized_sql = validate_participant_sql(raw_query)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query Validation Error: {str(val_err)}",
        )

    start_time = time.perf_counter()

    async with pool.acquire() as conn:
        try:
            # Execute inside an explicit read-only transaction with timeout
            async with conn.transaction(readonly=True):
                # Set statement timeout for this specific query run
                await conn.execute(f"SET LOCAL statement_timeout = '{settings.STATEMENT_TIMEOUT_MS}ms';")
                # Set search path strictly to investigation
                await conn.execute("SET LOCAL search_path = investigation;")

                # Execute query
                # Use prepare to extract column names and stream/fetch rows
                stmt = await conn.prepare(sanitized_sql)
                attributes = stmt.get_attributes()
                columns = [attr.name for attr in attributes]

                # Fetch rows capped at MAX_QUERY_ROWS
                raw_rows = await stmt.fetch()
                capped_rows = raw_rows[: settings.MAX_QUERY_ROWS]

                rows: List[List[Any]] = [
                    [sanitize_cell_value(val) for val in row.values()]
                    for row in capped_rows
                ]

        except asyncpg.QueryCanceledError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query execution timed out ({settings.STATEMENT_TIMEOUT_MS / 1000.0}s limit exceeded). Optimize your query.",
            )
        except asyncpg.PostgresSyntaxError as syntax_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SQL Syntax Error: {syntax_err.message}",
            )
        except asyncpg.InsufficientPrivilegeError as priv_err:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: You do not have permission to access that schema or table.",
            )
        except asyncpg.PostgresError as pg_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database Error: {pg_err.message}",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute query: {str(exc)}",
            )

    execution_time = round((time.perf_counter() - start_time) * 1000.0, 2)

    return QueryExecuteResponse(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=execution_time,
    )
