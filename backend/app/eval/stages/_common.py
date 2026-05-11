"""Shared utilities for per-node eval stage runners."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.eval.models import StageReport, StageSummary


def fixtures_dir() -> Path:
    """Return the canonical eval fixtures directory."""
    return Path(__file__).resolve().parent.parent / "fixtures"


def load_stage_fixtures(name: str) -> list[dict[str, Any]]:
    """Load a per-stage fixture JSON file as a list of plain dicts."""
    path = fixtures_dir() / f"{name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Stage fixture {name!r} must be a JSON array")
    return payload


def tokenize(text: str | None) -> set[str]:
    """Lowercase alphanumeric tokenization used by overlap heuristics."""
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(left: str | None, right: str | None) -> float:
    """Return the Jaccard overlap between two token sets."""
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def build_stage_report(
    *,
    stage: str,
    results: list,
    deterministic_only: bool,
) -> StageReport:
    """Aggregate per-case results into a StageReport with summary stats.

    Args:
        stage: Stage name (registry key).
        results: List of StageCaseResult instances.
        deterministic_only: Whether the run skipped the LLM judge.
    """
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failures = [r.case_id for r in results if not r.passed]
    judge_scores = [
        r.judge.aggregate
        for r in results
        if r.judge is not None and r.judge.enabled and r.judge.aggregate is not None
    ]
    summary = StageSummary(
        stage=stage,
        total_cases=total,
        pass_rate=round(passed / total, 4) if total else 0.0,
        avg_judge_score=(round(sum(judge_scores) / len(judge_scores), 4) if judge_scores else None),
        failures=failures,
        deterministic_only=deterministic_only,
    )
    return StageReport(summary=summary, results=results)
