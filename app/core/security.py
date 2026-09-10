"""
Security utilities:
1. Cryptographically secure opaque session token generation.
2. Participant SQL Query Validator & Sanitizer.
"""

import re
import secrets
import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import DDL, DML, Keyword


FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "EXECUTE",
    "SET",
    "RESET",
    "LOCK",
    "VACUUM",
    "CALL",
    "DO",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "RELEASE",
    "PREPARE",
    "DEALLOCATE",
    "IMPORT",
    "LOAD",
}

FORBIDDEN_SCHEMA_PATTERNS = [
    re.compile(r"\bgame\s*\.", re.IGNORECASE),
    re.compile(r"\bpg_catalog\s*\.", re.IGNORECASE),
    re.compile(r"\binformation_schema\s*\.", re.IGNORECASE),
]


def generate_session_token() -> str:
    """Generate a cryptographically secure 64-character hex token."""
    return secrets.token_hex(32)


def validate_participant_sql(raw_query: str) -> str:
    """
    Validates that a participant's submitted SQL query:
    1. Is non-empty.
    2. Contains exactly ONE statement (rejects multi-statement chaining).
    3. Is strictly a SELECT or read-only CTE query.
    4. Does not contain any forbidden keywords (DDL/DML/Transaction).
    5. Does not reference the 'game' schema or internal Postgres catalog tables.

    Raises ValueError with an explanatory message if invalid.
    Returns the sanitized single-statement query.
    """
    if not raw_query or not raw_query.strip():
        raise ValueError("Query cannot be empty.")

    # Strip SQL comments
    cleaned_query = sqlparse.format(
        raw_query.strip(),
        strip_comments=True,
    ).strip()

    if not cleaned_query:
        raise ValueError("Query cannot be empty or consist only of comments.")

    # Parse statements
    statements = [stmt for stmt in sqlparse.parse(cleaned_query) if str(stmt).strip()]

    if len(statements) == 0:
        raise ValueError("No valid SQL statement found.")

    if len(statements) > 1:
        raise ValueError("Multiple SQL statements are strictly forbidden. Submit only one query.")

    stmt: Statement = statements[0]
    query_str = str(stmt).strip()

    # Disallow semicolons inside statement that might lead to secondary executions
    # (Allow a single trailing semicolon)
    inner_code = query_str.rstrip(";")
    if ";" in inner_code:
        raise ValueError("Multiple SQL statements or chained commands are forbidden.")

    # Check for forbidden schema access
    for pattern in FORBIDDEN_SCHEMA_PATTERNS:
        if pattern.search(query_str):
            raise ValueError("Access to internal or protected schemas (e.g. 'game') is prohibited.")

    # Determine statement type
    stmt_type = stmt.get_type().upper()
    first_keyword = None
    for token in stmt.tokens:
        if not token.is_whitespace and token.ttype in (Keyword, DML, DDL):
            first_keyword = token.value.upper()
            break

    # Allow SELECT and WITH (Common Table Expressions that lead to SELECT)
    if stmt_type not in ("SELECT", "UNKNOWN") and first_keyword not in ("SELECT", "WITH"):
        raise ValueError(f"Only SELECT queries are permitted. Found: {stmt_type or first_keyword}")

    # Inspect all tokens for forbidden commands
    flattened_tokens = [t for t in stmt.flatten() if not t.is_whitespace]
    for token in flattened_tokens:
        val = token.value.upper()
        if val in FORBIDDEN_KEYWORDS:
            raise ValueError(f"Forbidden SQL keyword detected: {val}")

    return query_str
