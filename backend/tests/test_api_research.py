"""API tests for /research creation and SSE streaming behavior."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_research_create_and_stream_persists_report(api_client: TestClient) -> None:
    """Fallback research driver should stream events and persist one report."""
    create = api_client.post("/research", json={"topic": "fallback topic"})
    assert create.status_code == 200
    job_id = create.json()["job_id"]
    stream = api_client.get(f"/research/{job_id}/stream")
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers["content-type"]
    assert "[DONE]" in stream.text
    report = api_client.get(f"/reports/{job_id}")
    assert report.status_code == 200
    payload = report.json()
    assert payload["job_id"] == job_id
