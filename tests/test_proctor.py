"""
Test 15: Proctor violation tracking and auditing.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_proctor_violation_recorded(client: AsyncClient):
    """Test 15: Proctor violation is recorded properly in the database."""
    # Start session
    start_res = await client.post("/api/session/start", json={"username": "DETECTIVE-01"})
    token = start_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Log tab switch violation
    violation_payload = {
        "type": "TAB_SWITCH",
        "detail": "Participant switched browser tab away for 8 seconds.",
    }
    res = await client.post(
        "/api/proctor/violation",
        json=violation_payload,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "recorded"
    assert "violation_id" in data
    assert "recorded_at" in data
