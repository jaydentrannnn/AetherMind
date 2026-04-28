"""Deterministic, Ragas-style adapted metrics for offline eval."""

from __future__ import annotations

import re

from app.eval.models import EvalCitation, EvalFixtureCase, EvalMetrics


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return a bounded ratio and guard against divide-by-zero."""
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def _overlap_score(left: str, right: str) -> float:
    """Compute token overlap normalized by right-hand token count."""
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return _safe_ratio(len(left_tokens & right_tokens), len(right_tokens))


def faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """Approximate faithfulness via answer sentence support in retrieved contexts."""
    del question
    sentences = [s.strip() for s in re.split(r"[.!?]+", answer) if s.strip()]
    if not sentences:
        return 0.0
    if not contexts:
        return 0.0
    supported = 0
    for sentence in sentences:
        if any(_overlap_score(ctx, sentence) >= 0.5 for ctx in contexts):
            supported += 1
    return round(_safe_ratio(supported, len(sentences)), 4)


def answer_relevance(question: str, answer: str) -> float:
    """Approximate answer relevance via question-token coverage in the answer."""
    question_tokens = _tokenize(question)
    answer_tokens = _tokenize(answer)
    if not question_tokens or not answer_tokens:
        return 0.0
    covered = len(question_tokens & answer_tokens)
    return round(_safe_ratio(covered, len(question_tokens)), 4)


def citation_precision(answer: str, citations: list[EvalCitation]) -> float:
    """Approximate citation precision as share of citations supported by answer overlap."""
    if not citations:
        return 0.0
    supported = 0
    for citation in citations:
        if citation.snippet and _overlap_score(answer, citation.snippet) >= 0.3:
            supported += 1
    return round(_safe_ratio(supported, len(citations)), 4)


def compute_metrics(case: EvalFixtureCase) -> EvalMetrics:
    """Compute the deterministic metric bundle for one fixture case."""
    return EvalMetrics(
        faithfulness=faithfulness(case.question, case.answer, case.contexts),
        answer_relevance=answer_relevance(case.question, case.answer),
        citation_precision=citation_precision(case.answer, case.citations),
    )
