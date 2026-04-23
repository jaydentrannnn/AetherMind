"""API tests for report retrieval and version payload transforms."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_reports_404_for_unknown_id(api_client: TestClient) -> None:
    """Unknown report ids should return a 404 payload."""
    response = api_client.get("/reports/missing-id")
    assert response.status_code == 404


def test_reports_list_returns_jobs_for_default_user(api_client: TestClient) -> None:
    """GET /reports should return recent jobs with stable field names and ordering."""
    job_a = api_client.post("/research", json={"topic": "list ordering a"}).json()["job_id"]
    job_b = api_client.post("/research", json={"topic": "list ordering b"}).json()["job_id"]
    response = api_client.get("/reports?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    by_job = {row["job_id"]: row for row in payload}
    assert job_a in by_job and job_b in by_job
    for row in payload:
        assert set(row.keys()) == {"job_id", "topic", "status", "created_at", "latest_report_id"}
    # Newest job first
    idx_a = next(i for i, row in enumerate(payload) if row["job_id"] == job_a)
    idx_b = next(i for i, row in enumerate(payload) if row["job_id"] == job_b)
    assert idx_b < idx_a


def test_reports_payload_contains_ui_transform_fields(api_client: TestClient) -> None:
    """Report endpoint should expose transformed fields used by the frontend."""
    job = api_client.post("/research", json={"topic": "report transform"}).json()["job_id"]
    api_client.get(f"/research/{job}/stream")
    response = api_client.get(f"/reports/{job}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][0]["domain"] == "example.com"
    assert payload["trace_id"] == job
    versions = api_client.get(f"/reports/{job}/versions")
    assert versions.status_code == 200
    assert isinstance(versions.json(), list)
