"""
Tests 9-13: Participant SQL sandbox security tests.
Verifies SELECT works, write/DDL/multi-statement queries fail,
and access to game schema is blocked.
"""

import pytest
from httpx import AsyncClient
from app.core.security import validate_participant_sql


@pytest.mark.asyncio
async def test_participant_sql_select_works(client: AsyncClient):
    """Test 9: Participant SQL SELECT works properly."""
    # Start session
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Execute valid SELECT query
    query_res = await client.post(
        "/api/query/execute",
        json={"query": "SELECT * FROM crime_scene_log WHERE item = 'Vintage Fountain Pen';"},
        headers=headers,
    )
    assert query_res.status_code == 200
    data = query_res.json()
    assert "columns" in data
    assert "rows" in data
    assert data["row_count"] == 1
    assert "item" in data["columns"]


@pytest.mark.asyncio
async def test_participant_sql_insert_update_delete_fails(client: AsyncClient):
    """Test 10: INSERT/UPDATE/DELETE fails with 400 Bad Request."""
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    forbidden_queries = [
        "INSERT INTO crime_scene_log (item, location) VALUES ('Forged Clue', 'Desk');",
        "UPDATE suspects SET alibi = 'Innocent' WHERE name = 'Arthur Vance';",
        "DELETE FROM phone_records WHERE caller = 'Arthur Vance';",
    ]

    for q in forbidden_queries:
        res = await client.post(
            "/api/query/execute",
            json={"query": q},
            headers=headers,
        )
        assert res.status_code == 400
        assert "forbidden" in res.json()["detail"].lower() or "only select" in res.json()["detail"].lower()

    # Also test direct validator
    for q in forbidden_queries:
        with pytest.raises(ValueError) as exc:
            validate_participant_sql(q)
        assert "forbidden" in str(exc.value).lower() or "only select" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_participant_sql_drop_fails(client: AsyncClient):
    """Test 11: DROP table/database fails."""
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    drop_query = "DROP TABLE suspects;"
    res = await client.post(
        "/api/query/execute",
        json={"query": drop_query},
        headers=headers,
    )
    assert res.status_code == 400
    assert "forbidden" in res.json()["detail"].lower() or "only select" in res.json()["detail"].lower()

    with pytest.raises(ValueError):
        validate_participant_sql(drop_query)


@pytest.mark.asyncio
async def test_participant_sql_multiple_statements_fail(client: AsyncClient):
    """Test 12: Multiple SQL statements (statement chaining) fail."""
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    multi_query = "SELECT * FROM suspects; SELECT * FROM crime_scene_log;"
    res = await client.post(
        "/api/query/execute",
        json={"query": multi_query},
        headers=headers,
    )
    assert res.status_code == 400
    assert "multiple sql statements" in res.json()["detail"].lower()

    with pytest.raises(ValueError) as exc:
        validate_participant_sql(multi_query)
    assert "multiple" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_participant_cannot_access_game_schema(client: AsyncClient):
    """Test 13: Querying the game schema (answers/participants/sessions) is blocked."""
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    sneaky_queries = [
        "SELECT correct_answer FROM game.levels;",
        "SELECT * FROM game.participants;",
        "SELECT token FROM game.sessions;",
        "SELECT * FROM game.penalties;",
    ]

    for q in sneaky_queries:
        res = await client.post(
            "/api/query/execute",
            json={"query": q},
            headers=headers,
        )
        assert res.status_code == 400
        assert "game" in res.json()["detail"].lower() or "prohibited" in res.json()["detail"].lower()

    # Direct validator check
    for q in sneaky_queries:
        with pytest.raises(ValueError) as exc:
            validate_participant_sql(q)
        assert "game" in str(exc.value).lower() or "prohibited" in str(exc.value).lower()
