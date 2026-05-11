"""Guardrails-stage eval: policy + citation closure precision/recall.

Deterministic only — overlap-based closure verification short-circuits before
any entailment call when fixtures stage their snippets above the overlap
threshold. Unknown source ids never reach the entailment branch.
"""

from __future__ import annotations

from typing import Any

from app.agent.nodes.guardrails import guardrails_node
from app.eval.models import StageCaseResult, StageReport
from app.eval.stages._common import build_stage_report, load_stage_fixtures
from app.schemas import Report, Source


async def run_guardrails_stage(
    *,
    mock_llm: bool = False,
    deterministic_only: bool = True,
) -> StageReport:
    """Run labeled guardrail fixtures and compare against expected counts.

    Args:
        mock_llm: Unused (guardrails stage runs without LLM by design).
        deterministic_only: Always True for this stage; kept for interface
            symmetry with other stage runners.
    """
    del mock_llm
    cases = load_stage_fixtures("guardrails")
    results: list[StageCaseResult] = []

    for case in cases:
        case_id = case["case_id"]
        sources = [Source.model_validate(s) for s in case.get("sources", [])]
        draft = Report.model_validate(case["draft"])
        memory_context = case.get("memory_context", {})
        expected = case.get("expected", {})

        try:
            state_out = await guardrails_node(
                {
                    "draft": draft,
                    "sources": sources,
                    "memory_context": memory_context,
                }
            )
        except Exception as exc:
            results.append(
                StageCaseResult(
                    case_id=case_id,
                    passed=False,
                    deterministic={"error": True},
                    diagnostics=[f"guardrails_node raised: {exc!r}"],
                )
            )
            continue

        report = state_out["guardrail_report"]
        verified_claims = sum(
            1
            for section in draft.sections
            for claim in section.claims
            for citation in claim.citations
            if citation.verified
        )

        deterministic: dict[str, Any] = {
            "policy_violations": len(report.policy_violations),
            "closure_violations": len(report.closure_violations),
            "unverified_claims": len(report.unverified_claims),
            "verified_claims": verified_claims,
        }

        diagnostics: list[str] = []
        if "policy_violations" in expected and deterministic["policy_violations"] != expected["policy_violations"]:
            diagnostics.append(
                f"policy_violations={deterministic['policy_violations']} expected {expected['policy_violations']}"
            )
        if "closure_violations" in expected and deterministic["closure_violations"] != expected["closure_violations"]:
            diagnostics.append(
                f"closure_violations={deterministic['closure_violations']} expected {expected['closure_violations']}"
            )
        if "min_verified_claims" in expected and verified_claims < expected["min_verified_claims"]:
            diagnostics.append(
                f"verified_claims={verified_claims} < {expected['min_verified_claims']}"
            )

        results.append(
            StageCaseResult(
                case_id=case_id,
                passed=(not diagnostics),
                deterministic=deterministic,
                diagnostics=diagnostics,
            )
        )

    return build_stage_report(
        stage="guardrails",
        results=results,
        deterministic_only=True,
    )
