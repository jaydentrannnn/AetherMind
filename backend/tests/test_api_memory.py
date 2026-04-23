"""API tests for memory preferences and semantic search endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_memory_preferences_round_trip(api_client: TestClient) -> None:
    """Memory preferences should save and load with allow/deny domain lists."""
    payload = {
        "preferences": [
            {"key": "tone", "value": "concise", "source": "user", "updatedAt": "2026-04-22T00:00:00Z"}
        ],
        "allow_domains": ["arxiv.org"],
        "deny_domains": ["spam.example"],
    }
    saved = api_client.post("/memory/preferences", json=payload)
    assert saved.status_code == 200
    loaded = api_client.get("/memory/preferences")
    assert loaded.status_code == 200
    body = loaded.json()
    assert body["allow_domains"] == ["arxiv.org"]
    assert body["deny_domains"] == ["spam.example"]


def test_memory_search_returns_well_formed_results(api_client: TestClient) -> None:
    """Semantic search should return a query echo and list payload."""
    job_id = api_client.post("/research", json={"topic": "semantic lookup topic"}).json()["job_id"]
    api_client.get(f"/research/{job_id}/stream")
    response = api_client.get("/memory/search", params={"q": "semantic"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "semantic"
    assert isinstance(body["results"], list)
