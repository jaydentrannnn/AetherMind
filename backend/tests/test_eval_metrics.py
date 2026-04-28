"""Tests for deterministic eval metric calculations."""

from __future__ import annotations

from app.eval.metrics import answer_relevance, citation_precision, compute_metrics, faithfulness
from app.eval.models import EvalCitation, EvalFixtureCase


def test_faithfulness_scores_sentence_support() -> None:
    """Faithfulness should count answer sentences supported by contexts."""
    score = faithfulness(
        "q",
        "alpha beta. unsupported words.",
        ["alpha beta gamma"],
    )
    assert 0.0 < score < 1.0


def test_answer_relevance_uses_question_token_coverage() -> None:
    """Answer relevance should reflect overlap with question terms."""
    score = answer_relevance("benefits of tests", "tests provide benefits")
    assert score > 0.0


def test_citation_precision_requires_overlap() -> None:
    """Citation precision should reward overlapping citation snippets."""
    citations = [
        EvalCitation(source_id="a", snippet="tests catch regressions"),
        EvalCitation(source_id="b", snippet="completely unrelated"),
    ]
    score = citation_precision("tests catch regressions quickly", citations)
    assert 0.0 < score < 1.0


def test_compute_metrics_returns_bounded_values() -> None:
    """Metric bundle should always stay inside the [0, 1] range."""
    case = EvalFixtureCase(
        case_id="x",
        question="why tests",
        answer="tests catch regressions",
        contexts=["tests catch regressions"],
        citations=[EvalCitation(source_id="1", snippet="tests catch regressions")],
    )
    metrics = compute_metrics(case)
    assert 0.0 <= metrics.faithfulness <= 1.0
    assert 0.0 <= metrics.answer_relevance <= 1.0
    assert 0.0 <= metrics.citation_precision <= 1.0
