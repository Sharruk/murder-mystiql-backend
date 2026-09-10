"""
Tests 4-8: Gameplay mechanics, answer submissions, wrong answer locks/penalties, hints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_correct_answer_unlocks_next_level(client: AsyncClient):
    """Test 4: Correct answer unlocks next level."""
    # Start session
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify starting at Level 1
    lvl_res = await client.get("/api/level/current", headers=headers)
    assert lvl_res.status_code == 200
    assert lvl_res.json()["order_no"] == 1

    # Submit correct answer for Level 1 ('A.V.')
    submit_res = await client.post(
        "/api/answer/submit",
        json={"answer": "A.V."},
        headers=headers,
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["is_correct"] is True
    assert submit_data["completed"] is False
    assert submit_data["next_level_order"] == 2

    # Verify current level is now Level 2
    lvl2_res = await client.get("/api/level/current", headers=headers)
    assert lvl2_res.status_code == 200
    assert lvl2_res.json()["order_no"] == 2
    assert "suspects" in lvl2_res.json()["unlocks_tables"]


@pytest.mark.asyncio
async def test_wrong_answer_applies_5min_penalty(client: AsyncClient):
    """Test 5: Wrong answer applies 5-minute penalty (300 seconds)."""
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    submit_res = await client.post(
        "/api/answer/submit",
        json={"answer": "WRONG_ANSWER"},
        headers=headers,
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["is_correct"] is False
    assert submit_data["penalty_applied_seconds"] == 300


@pytest.mark.asyncio
async def test_wrong_answer_applies_1min_lock(client: AsyncClient):
    """Test 6: Wrong answer applies 1-minute lock (60 seconds)."""
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    submit_res = await client.post(
        "/api/answer/submit",
        json={"answer": "WRONG_ANSWER"},
        headers=headers,
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["is_locked"] is True
    assert submit_data["remaining_lock_seconds"] > 0
    assert submit_data["remaining_lock_seconds"] <= 60


@pytest.mark.asyncio
async def test_locked_participant_cannot_submit(client: AsyncClient):
    """Test 7: Locked participant cannot submit another answer (returns 409 Conflict)."""
    # Start session
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit wrong answer to trigger lock
    await client.post(
        "/api/answer/submit",
        json={"answer": "WRONG_ANSWER"},
        headers=headers,
    )

    # Attempt to submit again immediately while locked
    locked_res = await client.post(
        "/api/answer/submit",
        json={"answer": "A.V."},
        headers=headers,
    )
    assert locked_res.status_code == 409
    assert "locked" in locked_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hint_applies_configured_penalty(client: AsyncClient):
    """Test 8: Hint applies configured penalty and is idempotent."""
    # Start session
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Request hint for Level 1 (configured hint penalty: 120 seconds)
    hint_res = await client.post("/api/hint/request", headers=headers)
    assert hint_res.status_code == 200
    hint_data = hint_res.json()
    assert hint_data["level_order"] == 1
    assert "crime scene log" in hint_data["hint_text"].lower()
    assert hint_data["penalty_applied_seconds"] == 120
    assert hint_data["is_already_revealed"] is False

    # Request hint again (idempotent - no repeated penalty)
    hint2_res = await client.post("/api/hint/request", headers=headers)
    assert hint2_res.status_code == 200
    hint2_data = hint2_res.json()
    assert hint2_data["penalty_applied_seconds"] == 0
    assert hint2_data["is_already_revealed"] is True
