"""Researcher-stage eval runner: tool fan-out, source closure, dedup, evidence."""

from __future__ import annotations

from typing import Any

from app.agent.depth import normalize_depth
from app.agent.nodes.researcher import researcher_node
from app.agent.state import reduce_sources
from app.eval.judges import score_finding
from app.eval.models import StageCaseResult, StageReport
from app.eval.stages._common import build_stage_report, load_stage_fixtures
from app.eval.stubs import StubToolSpec, stub_tool_catalog
from app.schemas import SubQuestion


def _deterministic_checks(
    *,
    finding,
    sources: list,
    expected: dict[str, Any],
    dedup_url: str | None,
) -> tuple[bool, dict[str, Any], list[str]]:
    """Validate that the researcher's output respects source closure and dedup.

    The reducer (`reduce_sources`) is what enforces URL-level dedup at the
    graph level; we run it explicitly on the node output here to verify it
    collapses fixtures that share a URL.
    """
    diagnostics: list[str] = []
    source_ids = {src.id for src in sources}
    closure_ok = all(sid in source_ids for sid in finding.source_ids)
    metrics: dict[str, Any] = {
        "source_count": len(sources),
        "evidence_lines": len(finding.evidence),
        "source_closure_ok": closure_ok,
    }

    if not closure_ok:
        missing = [sid for sid in finding.source_ids if sid not in source_ids]
        diagnostics.append(f"finding references unregistered source ids: {missing}")

    min_sources = expected.get("min_sources", 1)
    if len(sources) < min_sources:
        diagnostics.append(f"too few sources: {len(sources)} < {min_sources}")

    min_evidence = expected.get("min_evidence_lines", 1)
    if len(finding.evidence) < min_evidence:
        diagnostics.append(f"too few evidence lines: {len(finding.evidence)} < {min_evidence}")

    if dedup_url is not None:
        deduped = reduce_sources([], list(sources))
        matching = [s for s in deduped if (s.url_or_doi or "") == dedup_url]
        metrics["dedup_collapsed_to"] = len(matching)
        if len(matching) != 1:
            diagnostics.append(
                f"reduce_sources failed to collapse {dedup_url!r} to a single "
                f"entry (got {len(matching)})"
            )

    return (not diagnostics), metrics, diagnostics


async def run_researcher_stage(
    *,
    mock_llm: bool = False,
    deterministic_only: bool = False,
) -> StageReport:
    """Evaluate the researcher node with stubbed tool catalogs.

    Args:
        mock_llm: Researcher itself never calls the LLM, so this flag only
            disables the evidence-quality judge.
        deterministic_only: When True, skip the researcher_judge call.
    """
    cases = load_stage_fixtures("researcher")
    results: list[StageCaseResult] = []
    skip_judge = mock_llm or deterministic_only

    for case in cases:
        case_id = case["case_id"]
        topic = case["topic"]
        depth = normalize_depth(case.get("depth"))
        sub_question = SubQuestion(**case["sub_question"])
        stub_specs = {
            tool_name: StubToolSpec.model_validate(spec)
            for tool_name, spec in case.get("stub_tools", {}).items()
        }
        expected = case.get("expected", {})
        dedup_url = expected.get("dedup_url")

        try:
            with stub_tool_catalog(stub_specs):
                state = await researcher_node(
                    {
                        "topic": topic,
                        "depth": depth,
                        "sub_question": sub_question,
                    }
                )
            findings = state.get("findings", [])
            sources = state.get("sources", [])
            if not findings:
                results.append(
                    StageCaseResult(
                        case_id=case_id,
                        passed=False,
                        deterministic={"source_count": len(sources)},
                        diagnostics=["researcher returned no findings"],
                        judge=None,
                    )
                )
                continue
            finding = findings[0]
            passed, metrics, diagnostics = _deterministic_checks(
                finding=finding,
                sources=sources,
                expected=expected,
                dedup_url=dedup_url,
            )
        except Exception as exc:
            results.append(
                StageCaseResult(
                    case_id=case_id,
                    passed=False,
                    deterministic={"error": True},
                    diagnostics=[f"researcher_node raised: {exc!r}"],
                    judge=None,
                )
            )
            continue

        judge_result = None
        if not skip_judge:
            judge_result = await score_finding(
                sub_question=sub_question,
                finding=finding,
                sources=sources,
            )

        results.append(
            StageCaseResult(
                case_id=case_id,
                passed=passed,
                deterministic=metrics,
                diagnostics=diagnostics,
                judge=judge_result,
            )
        )

    return build_stage_report(
        stage="researcher",
        results=results,
        deterministic_only=skip_judge,
    )
