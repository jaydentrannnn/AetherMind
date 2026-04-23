"""API tests for feedback persistence endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_feedback_persists_for_report(api_client: TestClient) -> None:
    """Posting feedback should create a feedback row response."""
    job_id = api_client.post("/research", json={"topic": "feedback test"}).json()["job_id"]
    api_client.get(f"/research/{job_id}/stream")
    report = api_client.get(f"/reports/{job_id}").json()
    response = api_client.post(
        "/feedback",
        json={"report_id": report["id"], "accepted": True, "user_comment": "Nice output"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["created_at"]
