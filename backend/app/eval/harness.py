"""Offline eval harness CLI: legacy fixture mode plus per-node stage mode."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.eval.fixtures import default_fixtures_path, load_fixtures
from app.eval.judge import EvalJudge
from app.eval.metrics import compute_metrics
from app.eval.models import (
    EvalCaseResult,
    EvalRunReport,
    EvalRunSummary,
    StageReport,
)
from app.eval.stages import STAGE_NAMES, STAGE_REGISTRY
from app.eval.tracing import build_eval_tracer

_STAGE_CHOICES: tuple[str, ...] = ("legacy", *STAGE_NAMES, "all")


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for `python -m app.eval.harness`."""
    parser = argparse.ArgumentParser(description="Run AetherMind offline eval harness")
    parser.add_argument(
        "--stage",
        choices=_STAGE_CHOICES,
        default="legacy",
        help=(
            "Which eval to run: 'legacy' for the fixture-based output-only eval, "
            "a stage name for one node-level eval, or 'all' for every stage."
        ),
    )
    parser.add_argument(
        "--fixtures",
        type=str,
        default=str(default_fixtures_path()),
        help="Path to legacy eval fixtures JSON file (only used when --stage=legacy)",
    )
    parser.add_argument("--max-cases", type=int, default=None, help="Optional cap for number of cases")
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional path to write JSON report",
    )
    parser.add_argument(
        "--deterministic-only",
        action="store_true",
        help="Skip LLM judge calls and compute deterministic metrics only",
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Use deterministic router stubs for stages whose nodes call the LLM",
    )
    return parser


def _average(values: list[float]) -> float:
    """Compute a safe average for metric vectors."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


async def run_eval(
    *,
    fixtures_path: str,
    max_cases: int | None = None,
    deterministic_only: bool = False,
) -> EvalRunReport:
    """Run the legacy fixture-based eval suite and return a structured report."""
    cases = load_fixtures(fixtures_path, max_cases=max_cases)
    judge = EvalJudge()
    effective_deterministic = deterministic_only or not judge.is_configured()
    disabled_reason = "deterministic_only enabled" if deterministic_only else None
    if not deterministic_only and not judge.is_configured():
        disabled_reason = "MODEL_EVAL_JUDGE is not configured"
    tracer = build_eval_tracer()
    tracer.start_run(
        total_cases=len(cases),
        deterministic_only=effective_deterministic,
        fixtures_path=fixtures_path,
    )

    results: list[EvalCaseResult] = []
    for case in cases:
        span = tracer.start_case(case_id=case.case_id)
        metrics = compute_metrics(case)
        judge_result = await judge.score(
            question=case.question,
            answer=case.answer,
            contexts=case.contexts,
            metric_snapshot=metrics.model_dump(),
            disabled_reason=disabled_reason if effective_deterministic else None,
        )
        results.append(EvalCaseResult(case_id=case.case_id, metrics=metrics, judge=judge_result))
        tracer.end_case(
            span,
            metrics=metrics.model_dump(),
            judge_enabled=judge_result.enabled,
        )

    avg_faithfulness = _average([row.metrics.faithfulness for row in results])
    avg_answer_relevance = _average([row.metrics.answer_relevance for row in results])
    avg_citation_precision = _average([row.metrics.citation_precision for row in results])
    avg_deterministic_score = _average([row.metrics.mean() for row in results])
    judge_scores = [row.judge.aggregate for row in results if row.judge.enabled and row.judge.aggregate is not None]
    summary = EvalRunSummary(
        total_cases=len(results),
        deterministic_only=effective_deterministic,
        fixtures_path=fixtures_path,
        avg_faithfulness=avg_faithfulness,
        avg_answer_relevance=avg_answer_relevance,
        avg_citation_precision=avg_citation_precision,
        avg_deterministic_score=avg_deterministic_score,
        avg_judge_score=_average(judge_scores) if judge_scores else None,
    )
    tracer.end_run(summary=summary.model_dump())
    return EvalRunReport(summary=summary, results=results)


async def run_stage_eval(
    *,
    stages: list[str],
    mock_llm: bool = False,
    deterministic_only: bool = False,
) -> EvalRunReport:
    """Run one or more per-node stage evals and return an aggregated report.

    Args:
        stages: Stage names to run (each must be a key of ``STAGE_REGISTRY``).
        mock_llm: When True, stages use deterministic router stubs in place of
            their LLM call (where applicable).
        deterministic_only: When True, stages skip their LLM-as-judge step.
    """
    if not stages:
        raise ValueError("run_stage_eval requires at least one stage name")
    unknown = [s for s in stages if s not in STAGE_REGISTRY]
    if unknown:
        raise ValueError(f"unknown stages: {unknown}; valid choices: {STAGE_NAMES}")

    stage_reports: dict[str, StageReport] = {}
    for stage in stages:
        runner = STAGE_REGISTRY[stage]
        stage_reports[stage] = await runner(
            mock_llm=mock_llm,
            deterministic_only=deterministic_only,
        )

    total_cases = sum(report.summary.total_cases for report in stage_reports.values())
    judge_scores = [
        report.summary.avg_judge_score
        for report in stage_reports.values()
        if report.summary.avg_judge_score is not None
    ]
    avg_judge_score = round(sum(judge_scores) / len(judge_scores), 4) if judge_scores else None

    summary = EvalRunSummary(
        total_cases=total_cases,
        deterministic_only=deterministic_only or mock_llm,
        fixtures_path="per-node",
        avg_judge_score=avg_judge_score,
        stages={name: report.summary for name, report in stage_reports.items()},
    )
    return EvalRunReport(summary=summary, results=[], stages=stage_reports)


def _resolve_stages(stage_arg: str) -> list[str]:
    """Convert the --stage CLI value into the explicit list of stage names."""
    if stage_arg == "all":
        return list(STAGE_NAMES)
    return [stage_arg]


async def _async_main() -> int:
    """Run CLI entrypoint and print/write JSON report."""
    args = _build_parser().parse_args()
    if args.stage == "legacy":
        report = await run_eval(
            fixtures_path=args.fixtures,
            max_cases=args.max_cases,
            deterministic_only=args.deterministic_only,
        )
    else:
        report = await run_stage_eval(
            stages=_resolve_stages(args.stage),
            mock_llm=args.mock_llm,
            deterministic_only=args.deterministic_only,
        )
    payload = report.model_dump()
    rendered = json.dumps(payload, indent=2, default=str)
    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


def main() -> int:
    """Synchronous wrapper for module execution."""
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
