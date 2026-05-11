"""Critic-stage eval: routing decisions, revision budget, optional rubric judge."""

from __future__ import annotations

from typing import Any

from app.agent.depth import normalize_depth
from app.agent.nodes.critic import critic_node
from app.config import settings
from app.eval.judges import score_critic
from app.eval.models import StageCaseResult, StageReport
from app.eval.stages._common import build_stage_report, load_stage_fixtures
from app.llm.router import TaskTag
from app.schemas import Critique, GuardrailReport, Report


class _MockCriticRouter:
    """Router stub that returns a fixture-provided Critique for the critic node.

    The critic node calls ``router.structured("critic_inner"|"critic_final", ...)``
    once per invocation. We return the same fixture critique regardless of
    which inner/final variant is requested to keep routing tests deterministic.
    """

    def __init__(self, critique: Critique) -> None:
        """Cache the fixture critique returned for every call."""
        self._critique = critique

    async def structured(self, task: TaskTag, messages: list[dict[str, Any]], schema, **kwargs):
        """Return the cached Critique when the critic task is invoked."""
        del messages, kwargs
        if task not in {"critic_inner", "critic_final"}:
            raise AssertionError(f"_MockCriticRouter only handles critic tasks, got {task!r}")
        if schema is not Critique:
            raise AssertionError(f"_MockCriticRouter expects Critique, got {schema!r}")
        return self._critique


async def run_critic_stage(
    *,
    mock_llm: bool = True,
    deterministic_only: bool = False,
) -> StageReport:
    """Validate critic routing decisions and the revision budget guard.

    Args:
        mock_llm: When True (default), the critic's LLM call is replaced by a
            fixture-provided Critique so routing assertions stay deterministic.
            When False, the real critic LLM runs; routing assertions are then
            best-effort but the rubric judge still scores quality.
        deterministic_only: When True, skip the critic_judge LLM call.
    """
    cases = load_stage_fixtures("critic")
    results: list[StageCaseResult] = []

    for case in cases:
        case_id = case["case_id"]
        topic = case["topic"]
        depth = normalize_depth(case.get("depth"))
        revisions = case.get("revisions", 0)
        draft = Report.model_validate(case["draft"])
        guardrail_report = GuardrailReport.model_validate(
            case.get("guardrail_report") or {}
        )
        expected_next = case.get("expected", {}).get("next_action")

        critique_fixture = Critique.model_validate(case["mock_critique"])
        llm_router = _MockCriticRouter(critique_fixture) if mock_llm else None

        try:
            state_out = await critic_node(
                {
                    "topic": topic,
                    "depth": depth,
                    "draft": draft,
                    "findings": [],
                    "guardrail_report": guardrail_report,
                    "revisions": revisions,
                },
                llm_router=llm_router,  # type: ignore[arg-type]
            )
        except Exception as exc:
            results.append(
                StageCaseResult(
                    case_id=case_id,
                    passed=False,
                    deterministic={"error": True},
                    diagnostics=[f"critic_node raised: {exc!r}"],
                )
            )
            continue

        next_action = state_out.get("next_action")
        new_revisions = state_out.get("revisions", revisions + 1)
        max_allowed = settings.AGENT_MAX_REVISIONS + 1  # +1 for "deep" extra

        diagnostics: list[str] = []
        if expected_next and next_action != expected_next:
            diagnostics.append(f"next_action={next_action!r} expected {expected_next!r}")
        if new_revisions > max_allowed + 1:
            diagnostics.append(
                f"revisions counter {new_revisions} exceeds plausible bound {max_allowed + 1}"
            )

        deterministic: dict[str, Any] = {
            "next_action": next_action,
            "revisions": new_revisions,
            "approved": state_out.get("approved", False),
        }

        judge_result = None
        if not mock_llm:
            # Only meaningful when the real critic produced the critique.
            judge_result = await score_critic(
                draft=draft,
                critique=state_out.get("critique") or critique_fixture,
                disabled_reason=(
                    "deterministic_only enabled" if deterministic_only else None
                ),
            )

        results.append(
            StageCaseResult(
                case_id=case_id,
                passed=(not diagnostics),
                deterministic=deterministic,
                diagnostics=diagnostics,
                judge=judge_result,
            )
        )

    return build_stage_report(
        stage="critic",
        results=results,
        deterministic_only=deterministic_only or mock_llm,
    )
