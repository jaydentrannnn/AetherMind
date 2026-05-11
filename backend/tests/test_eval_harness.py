"""Tests for offline eval harness orchestration and run summary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import settings
from app.eval.harness import run_eval, run_stage_eval
from app.eval.judge import EvalJudge, JudgeResult, JudgeRubric


def _write_fixtures(path: Path) -> None:
    """Write a minimal two-case fixture file for harness tests."""
    payload = [
        {
            "case_id": "c1",
            "question": "why tests",
            "answer": "tests catch regressions",
            "contexts": ["tests catch regressions early"],
            "citations": [{"source_id": "s1", "snippet": "tests catch regressions"}],
        },
        {
            "case_id": "c2",
            "question": "why docs",
            "answer": "docs help onboarding",
            "contexts": ["documentation helps onboarding"],
            "citations": [{"source_id": "s2", "snippet": "docs help onboarding"}],
        },
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


async def test_run_eval_defaults_to_deterministic_when_model_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harness should auto-disable judge when MODEL_EVAL_JUDGE is missing."""
    fixture_path = tmp_path / "fixtures.json"
    _write_fixtures(fixture_path)
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", None)
    report = await run_eval(fixtures_path=str(fixture_path))
    assert report.summary.deterministic_only is True
    assert report.summary.total_cases == 2
    assert all(not row.judge.enabled for row in report.results)


async def test_run_eval_supports_explicit_deterministic_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harness should skip judge calls when deterministic-only is requested."""
    fixture_path = tmp_path / "fixtures.json"
    _write_fixtures(fixture_path)
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", "openai/gpt-5.4-mini")
    report = await run_eval(fixtures_path=str(fixture_path), deterministic_only=True, max_cases=1)
    assert report.summary.total_cases == 1
    assert report.summary.deterministic_only is True
    assert report.summary.avg_judge_score is None


async def test_run_eval_includes_judge_scores_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harness should include judge aggregate when judge path is active."""
    fixture_path = tmp_path / "fixtures.json"
    _write_fixtures(fixture_path)
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", "openai/gpt-5.4-mini")

    async def _fake_score(self, **kwargs):  # noqa: ANN001
        """Return deterministic synthetic judge output for harness tests."""
        del self, kwargs
        return JudgeResult(
            enabled=True,
            model="openai/fake-mini",
            rubric=JudgeRubric(
                accuracy=4,
                completeness=4,
                citation_integrity=4,
                bias=4,
                structure=4,
                reasoning="ok",
            ),
            aggregate=4.0,
        )

    monkeypatch.setattr(EvalJudge, "score", _fake_score)
    report = await run_eval(fixtures_path=str(fixture_path))
    assert report.summary.deterministic_only is False
    assert report.summary.avg_judge_score == 4.0


async def test_run_stage_eval_planner_mock_llm_runs_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Planner stage with --mock-llm should pass deterministic band checks."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", None)
    report = await run_stage_eval(stages=["planner"], mock_llm=True, deterministic_only=True)
    assert "planner" in report.stages
    planner_summary = report.summary.stages["planner"]
    assert planner_summary.total_cases > 0
    assert planner_summary.pass_rate == 1.0
    assert report.summary.deterministic_only is True
    assert report.results == []


async def test_run_stage_eval_researcher_uses_stub_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Researcher stage should produce findings via stubbed tools without LLM."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", None)
    report = await run_stage_eval(
        stages=["researcher"], mock_llm=True, deterministic_only=True
    )
    researcher_summary = report.summary.stages["researcher"]
    assert researcher_summary.total_cases > 0
    assert researcher_summary.pass_rate == 1.0
    assert researcher_summary.failures == []


async def test_run_stage_eval_synthesizer_mock_llm_satisfies_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synth stage with mock router should pass citation closure checks."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", None)
    report = await run_stage_eval(
        stages=["synthesizer"], mock_llm=True, deterministic_only=True
    )
    synth_summary = report.summary.stages["synthesizer"]
    assert synth_summary.total_cases > 0
    for row in report.stages["synthesizer"].results:
        assert row.deterministic["citation_closure_ok"] is True


async def test_run_stage_eval_guardrails_matches_labeled_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardrails stage should match expected policy / closure violation counts."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", None)
    report = await run_stage_eval(
        stages=["guardrails"], mock_llm=False, deterministic_only=True
    )
    guard_summary = report.summary.stages["guardrails"]
    assert guard_summary.total_cases > 0
    assert guard_summary.pass_rate == 1.0


async def test_run_stage_eval_critic_routing_with_mock_critique(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Critic stage with mock_llm should match expected next_action labels."""
    monkeypatch.setattr(settings, "MODEL_EVAL_JUDGE", None)
    report = await run_stage_eval(
        stages=["critic"], mock_llm=True, deterministic_only=True
    )
    critic_summary = report.summary.stages["critic"]
    assert critic_summary.total_cases > 0
    assert critic_summary.pass_rate == 1.0


async def test_run_stage_eval_rejects_unknown_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_stage_eval should raise for unrecognized stage names."""
    del monkeypatch
    with pytest.raises(ValueError):
        await run_stage_eval(stages=["nonsense"], mock_llm=True, deterministic_only=True)
