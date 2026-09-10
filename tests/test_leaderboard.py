"""
Test 14: Leaderboard standings and effective time calculation.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_leaderboard_effective_time_and_ranking(client: AsyncClient):
    """Test 14: Leaderboard calculates effective time and ranks participants correctly."""
    # Participant 1 starts
    p1_start = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    t1 = p1_start.json()["token"]
    h1 = {"Authorization": f"Bearer {t1}"}

    # Participant 1 submits a wrong answer (+300s penalty)
    await client.post("/api/answer/submit", json={"answer": "WRONG"}, headers=h1)

    # Participant 2 starts
    p2_start = await client.post("/api/session/start", json={"username": "DETECTIVE-02"})
    t2 = p2_start.json()["token"]
    h2 = {"Authorization": f"Bearer {t2}"}

    # Participant 2 solves Level 1 immediately (0 penalties)
    await client.post("/api/answer/submit", json={"answer": "A.V."}, headers=h2)

    # Fetch leaderboard
    lb_res = await client.get("/api/leaderboard")
    assert lb_res.status_code == 200
    data = lb_res.json()
    assert data["total_participants"] >= 2

    entries = data["entries"]
    # Participant 2 has solved 1 level, Participant 1 has solved 0 levels
    # Participant 2 should be ranked higher (#1)
    p2_entry = next(e for e in entries if e["username"] == "DETECTIVE-02")
    p1_entry = next(e for e in entries if e["username"] == "DETECTIVE-01")

    assert p2_entry["rank"] == 1
    assert p2_entry["levels_solved"] == 1
    assert p2_entry["total_penalty_seconds"] == 0

    assert p1_entry["rank"] == 2
    assert p1_entry["levels_solved"] == 0
    assert p1_entry["total_penalty_seconds"] == 300
    assert p1_entry["wrong_answers_count"] == 1
    assert p1_entry["effective_time_seconds"] >= 300  # Elapsed + 300s penalty
