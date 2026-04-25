"""Tests for depth propagation into memory writer payloads."""

from __future__ import annotations

from app.agent.nodes.memory_writer import memory_writer_node


class FakeMemoryService:
    """Capture write payloads for assertions."""

    def __init__(self) -> None:
        """Initialize an empty list of observed writes."""
        self.calls: list[dict] = []

    async def write(self, payload: dict) -> dict:
        """Record one write payload and return a deterministic ack."""
        self.calls.append(payload)
        return {"report_id": "r-1"}


async def test_memory_writer_forwards_depth(monkeypatch) -> None:  # noqa: ANN001
    """memory_writer should include depth so persistence can round-trip it."""
    fake = FakeMemoryService()
    monkeypatch.setattr("app.agent.nodes.memory_writer.get_memory_service", lambda: fake)
    await memory_writer_node({"topic": "x", "depth": "deep"})
    assert len(fake.calls) == 1
    assert fake.calls[0]["depth"] == "deep"

