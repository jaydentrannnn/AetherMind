"""Tests for eval LLM-judge integration."""

from __future__ import annotations

import pytest

from app.config import settings
from app.eval.judge import EvalJudge, JudgeRubric


class FakeRouter:
    """Router stub returning deterministic judge rubric payloads."""

    def __init__(self) -> None:
        """Initialize test router state."""
        self.called = False

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Return a valid rubric and capture invocation."""
        del messages, schema, kwargs
        self.called = True
        assert task == "eval_judge"
        return JudgeRubric(
            accuracy=4,
            completeness=4,
            citation_integrity=5,
            bias=5,
            structure=4,
            reasoning="grounded",
        )

    def resolve(self, task):  # noqa: ANN001
        """Return a fake resolved model string for reporting."""
        assert task == "eval_judge"
        return "openai/fake-mini"


async def test_judge_returns_disabled_result_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Judge should short-circuit when no eval model is configured."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", None)
    result = await EvalJudge(llm_router=FakeRouter()).score(
        question="q",
        answer="a",
        contexts=[],
        metric_snapshot={"faithfulness": 0.0, "answer_relevance": 0.0, "citation_precision": 0.0},
    )
    assert result.enabled is False
    assert result.reason is not None


async def test_judge_calls_router_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Judge should call eval_judge task and emit aggregate score."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", "openai/gpt-5.4-mini")
    router = FakeRouter()
    result = await EvalJudge(llm_router=router).score(
        question="q",
        answer="a",
        contexts=["ctx"],
        metric_snapshot={"faithfulness": 1.0, "answer_relevance": 1.0, "citation_precision": 1.0},
    )
    assert router.called is True
    assert result.enabled is True
    assert result.aggregate is not None
    assert result.model == "openai/fake-mini"


async def test_judge_respects_explicit_disabled_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """Judge should skip router calls when deterministic mode is forced."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", "openai/gpt-5.4-mini")
    router = FakeRouter()
    result = await EvalJudge(llm_router=router).score(
        question="q",
        answer="a",
        contexts=[],
        metric_snapshot={"faithfulness": 0.0, "answer_relevance": 0.0, "citation_precision": 0.0},
        disabled_reason="deterministic_only enabled",
    )
    assert result.enabled is False
    assert result.reason == "deterministic_only enabled"
    assert router.called is False
