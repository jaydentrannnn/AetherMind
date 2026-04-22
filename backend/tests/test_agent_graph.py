"""Tests for graph fan-out and end-to-end routing behavior."""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.graph import _fan_out_from_plan, _route_after_critic, build_graph
from app.agent.nodes.planner import PlannerOutput
from app.schemas import Critique, EntailmentVerdict, Finding, PreferenceDeltaList, Report, Source, SubQuestion


class FakeRouter:
    """Return deterministic structured responses for graph tests."""

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Mock router.structured based on requested task tag."""
        del messages, kwargs
        if schema is PlannerOutput:
            return PlannerOutput(
                sub_questions=[
                    SubQuestion(
                        id="sq-1",
                        question="What changed?",
                        rationale="Cover scope",
                        suggested_tools=["web_search"],
                    )
                ]
            )
        if schema is Report:
            return Report(
                title="Draft",
                summary="Summary",
                markdown="Report body",
                sections=[],
            )
        if schema is Critique:
            return Critique(score=4.2, approved=True, directives=[])
        if schema is EntailmentVerdict:
            return EntailmentVerdict(entails=True, confidence=0.9)
        if schema is PreferenceDeltaList:
            return PreferenceDeltaList(deltas=[])
        raise AssertionError(f"unexpected schema {schema}")


class FakeMemoryService:
    """No-op memory service test double for graph integration tests."""

    async def recall(self, topic: str):  # noqa: ANN001
        """Return empty memory context without touching external stores."""
        del topic
        return {
            "preferences": {},
            "allow_domains": [],
            "deny_domains": [],
            "past_reports": [],
            "semantic_preferences": [],
        }

    async def write(self, payload):  # noqa: ANN001
        """Record payload shape and return a deterministic acknowledgment."""
        del payload
        return {"report_id": "fake"}


def test_fan_out_from_plan_returns_one_send_per_subquestion() -> None:
    """Planner fan-out should produce one Send envelope per planned item."""
    sends = _fan_out_from_plan(
        {
            "topic": "x",
            "plan": [
                SubQuestion(id="1", question="q1", suggested_tools=[]),
                SubQuestion(id="2", question="q2", suggested_tools=[]),
            ],
        }
    )
    assert len(sends) == 2


def test_route_after_critic_returns_send_list_for_research() -> None:
    """Critic next_action=researcher should trigger another fan-out list."""
    routed = _route_after_critic(
        {
            "topic": "x",
            "next_action": "researcher",
            "plan": [SubQuestion(id="1", question="q1", suggested_tools=[])],
        }
    )
    assert isinstance(routed, list)
    assert len(routed) == 1


async def test_build_graph_happy_path_with_mocked_researcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph should reach memory_writer when critic approves the draft."""

    async def _fake_researcher(state):  # noqa: ANN001
        """Return deterministic finding/source without external tool calls."""
        del state
        return {
            "findings": [Finding(sub_question_id="sq-1", answer="a", evidence=[], source_ids=[])],
            "sources": [Source(source_type="web_search", title="s", url_or_doi=None)],
        }

    monkeypatch.setattr("app.agent.graph.researcher_node", _fake_researcher)
    monkeypatch.setattr("app.agent.nodes.planner.get_memory_service", lambda: FakeMemoryService())
    monkeypatch.setattr("app.agent.nodes.memory_writer.get_memory_service", lambda: FakeMemoryService())
    graph = build_graph(llm_router=FakeRouter(), checkpointer=InMemorySaver())
    result = await graph.ainvoke(
        {"topic": "phase 5 test"},
        config={"configurable": {"thread_id": "test-thread-1"}},
    )
    assert result["approved"] is True
    assert result["draft"].title == "Draft"
    assert result["guardrail_report"] is not None


async def test_graph_runs_guardrails_between_synth_and_critic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph execution should include guardrails output before critic routing."""

    async def _fake_researcher(state):  # noqa: ANN001
        """Return one source and finding to feed synth/guardrail path."""
        del state
        return {
            "findings": [Finding(sub_question_id="sq-1", answer="a", evidence=[], source_ids=[])],
            "sources": [
                Source(
                    id="source-1",
                    source_type="web_search",
                    title="s",
                    url_or_doi="https://example.com",
                    snippet="alpha beta gamma",
                )
            ],
        }

    monkeypatch.setattr("app.agent.graph.researcher_node", _fake_researcher)
    monkeypatch.setattr("app.agent.nodes.planner.get_memory_service", lambda: FakeMemoryService())
    monkeypatch.setattr("app.agent.nodes.memory_writer.get_memory_service", lambda: FakeMemoryService())
    graph = build_graph(llm_router=FakeRouter(), checkpointer=InMemorySaver())
    result = await graph.ainvoke(
        {"topic": "phase 6 test"},
        config={"configurable": {"thread_id": "test-thread-2"}},
    )
    assert "guardrail_report" in result
    assert result["guardrail_report"] is not None
