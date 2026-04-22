"""Tests for critic loop routing decisions."""

from __future__ import annotations

import pytest

from app.agent.nodes.critic import critic_node
from app.config import settings
from app.schemas import Critique, Report


class RecordingRouter:
    """Capture the task tag chosen by critic_node and return a preset critique."""

    def __init__(self, critique: Critique) -> None:
        """Store a critique payload used for all calls."""
        self.critique = critique
        self.last_task: str | None = None

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Record the task and return the configured critique."""
        del messages, schema, kwargs
        self.last_task = task
        return self.critique


async def test_critic_routes_to_researcher_on_evidence_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evidence-gap directives should route back to researcher fan-out."""
    monkeypatch.setattr(settings, "AGENT_MAX_REVISIONS", 3)
    router = RecordingRouter(
        Critique(score=2.0, approved=False, directives=["Need more evidence from primary sources"])
    )
    result = await critic_node(
        {
            "topic": "x",
            "draft": Report(title="t", markdown="m", sections=[]),
            "revisions": 0,
            "findings": [],
        },
        llm_router=router,
    )
    assert router.last_task == "critic_inner"
    assert result["next_action"] == "researcher"


async def test_critic_uses_final_model_on_last_allowed_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Last allowed revision should use critic_final and exit loop."""
    monkeypatch.setattr(settings, "AGENT_MAX_REVISIONS", 2)
    router = RecordingRouter(Critique(score=2.2, approved=False, directives=["Improve structure"]))
    result = await critic_node(
        {
            "topic": "x",
            "draft": Report(title="t", markdown="m", sections=[]),
            "revisions": 1,
            "findings": [],
        },
        llm_router=router,
    )
    assert router.last_task == "critic_final"
    assert result["next_action"] == "memory_writer"
