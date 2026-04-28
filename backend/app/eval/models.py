"""Data models for offline evaluation harness inputs and outputs."""

from __future__ import annotations

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


class EvalRunSummary(BaseModel):
    """Aggregate scores and metadata for a full eval run."""

    total_cases: int
    deterministic_only: bool
    fixtures_path: str
    avg_faithfulness: float
    avg_answer_relevance: float
    avg_citation_precision: float
    avg_deterministic_score: float
    avg_judge_score: float | None = None


class EvalRunReport(BaseModel):
    """Top-level JSON report emitted by the harness CLI."""

    summary: EvalRunSummary
    results: list[EvalCaseResult]
