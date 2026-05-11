"""Data models for offline evaluation harness inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.eval.judge import JudgeResult


class EvalCitation(BaseModel):
    """Citation fixture entry used by citation precision metric."""

    source_id: str
    snippet: str = ""


class EvalFixtureCase(BaseModel):
    """One offline eval fixture case."""

    case_id: str
    question: str
    answer: str
    contexts: list[str] = Field(default_factory=list)
    citations: list[EvalCitation] = Field(default_factory=list)


class EvalMetrics(BaseModel):
    """Deterministic metric bundle for one fixture case."""

    faithfulness: float = Field(ge=0.0, le=1.0)
    answer_relevance: float = Field(ge=0.0, le=1.0)
    citation_precision: float = Field(ge=0.0, le=1.0)

    def mean(self) -> float:
        """Return the arithmetic mean across all deterministic metrics."""
        return round((self.faithfulness + self.answer_relevance + self.citation_precision) / 3.0, 4)


class EvalCaseResult(BaseModel):
    """Full result row for an evaluated fixture case."""

    case_id: str
    metrics: EvalMetrics
    judge: JudgeResult


class StageCaseResult(BaseModel):
    """Per-case result for one node-stage eval.

    `deterministic` is a free-form dict of metric/check names to numeric or
    boolean values produced by the stage runner. `diagnostics` captures
    human-readable reasons for any failed deterministic checks so the JSON
    report is debuggable without re-running the suite.
    """

    case_id: str
    passed: bool
    deterministic: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    judge: JudgeResult | None = None


class StageSummary(BaseModel):
    """Aggregate scores and metadata for one stage's eval run."""

    stage: str
    total_cases: int
    pass_rate: float
    avg_judge_score: float | None = None
    failures: list[str] = Field(default_factory=list)
    deterministic_only: bool = False


class StageReport(BaseModel):
    """Full report for one stage: summary plus per-case results."""

    summary: StageSummary
    results: list[StageCaseResult] = Field(default_factory=list)


class EvalRunSummary(BaseModel):
    """Aggregate scores and metadata for a full eval run."""

    total_cases: int
    deterministic_only: bool
    fixtures_path: str
    avg_faithfulness: float = 0.0
    avg_answer_relevance: float = 0.0
    avg_citation_precision: float = 0.0
    avg_deterministic_score: float = 0.0
    avg_judge_score: float | None = None
    stages: dict[str, StageSummary] = Field(default_factory=dict)


class EvalRunReport(BaseModel):
    """Top-level JSON report emitted by the harness CLI."""

    summary: EvalRunSummary
    results: list[EvalCaseResult] = Field(default_factory=list)
    stages: dict[str, StageReport] = Field(default_factory=dict)
