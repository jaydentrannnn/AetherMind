"""Tests for depth-aware planner output clamping."""

from __future__ import annotations

from app.agent.nodes.planner import PlannerOutput, planner_node
from app.schemas import SubQuestion


class FakeRouter:
    """Return an oversized planner output for clamping assertions."""

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Return ten deterministic sub-questions regardless of prompt."""
        del task, messages, schema, kwargs
        return PlannerOutput(
            sub_questions=[
                SubQuestion(id=f"sq-{index}", question=f"q{index}", suggested_tools=[])
                for index in range(10)
            ]
        )


class FakeMemoryService:
    """Return empty memory context for planner tests."""

    async def recall(self, topic: str):  # noqa: ANN001
        """Return stable empty recall payload."""
        del topic
        return {
            "preferences": {},
            "allow_domains": [],
            "deny_domains": [],
            "past_reports": [],
            "semantic_preferences": [],
        }


async def test_planner_clamps_to_quick_budget(monkeypatch) -> None:  # noqa: ANN001
    """Quick depth should clamp planner output to the quick max budget."""
    monkeypatch.setattr("app.agent.nodes.planner.get_memory_service", lambda: FakeMemoryService())
    result = await planner_node(
        {"topic": "x", "depth": "quick"},
        llm_router=FakeRouter(),
    )
    assert len(result["plan"]) == 3


async def test_planner_clamps_to_deep_budget(monkeypatch) -> None:  # noqa: ANN001
    """Deep depth should clamp planner output to the deep max budget."""
    monkeypatch.setattr("app.agent.nodes.planner.get_memory_service", lambda: FakeMemoryService())
    result = await planner_node(
        {"topic": "x", "depth": "deep"},
        llm_router=FakeRouter(),
    )
    assert len(result["plan"]) == 8

