"""
Tests 1-3: Session lifecycle, validation, and resumption.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_valid_participant_session_start(client: AsyncClient):
    """Test 1: Valid participant can start a session and receive a token."""
    response = await client.post(
        "/api/session/start",
        json={"username": "DETECTIVE-01"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert len(data["token"]) == 64  # 32 bytes hex
    assert data["participant"]["username"] == "DETECTIVE-01"
    assert data["participant"]["display_name"] == "Sherlock Holmes"
    assert data["current_level_order"] == 1
    assert data["is_locked"] is False
    assert data["is_completed"] is False


@pytest.mark.asyncio
async def test_unknown_username_rejected(client: AsyncClient):
    """Test 2: Unknown username rejected with 404."""
    response = await client.post(
        "/api/session/start",
        json={"username": "INVALID-USER-999"},
    )
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_existing_session_resumes(client: AsyncClient):
    """Test 3: Existing session resumes with the same token and preserved progress."""
    # First start
    res1 = await client.post(
        "/api/session/start",
        json={"username": "DETECTIVE-01"},
    )
    assert res1.status_code == 200
    token1 = res1.json()["token"]

    # Resume by calling start again with the same username (e.g. browser reload / re-login)
    res2 = await client.post(
        "/api/session/start",
        json={"username": "DETECTIVE-01"},
    )
    assert res2.status_code == 200
    token2 = res2.json()["token"]

    assert token1 == token2
    assert res2.json()["current_level_order"] == 1
