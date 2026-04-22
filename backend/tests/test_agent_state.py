"""Tests for agent state reducers."""

from __future__ import annotations

from app.agent.state import reduce_findings, reduce_sources
from app.schemas import Finding, Source


def test_reduce_findings_overwrites_by_sub_question_id() -> None:
    """Latest finding for a sub-question should replace earlier entries."""
    existing = [Finding(sub_question_id="q1", answer="old", evidence=[], source_ids=[])]
    incoming = [Finding(sub_question_id="q1", answer="new", evidence=[], source_ids=[])]
    reduced = reduce_findings(existing, incoming)
    assert len(reduced) == 1
    assert reduced[0].answer == "new"


def test_reduce_sources_dedupes_by_url_or_doi() -> None:
    """Sources with the same URL should collapse to one entry."""
    first = Source(source_type="web_search", title="A", url_or_doi="https://example.com")
    second = Source(source_type="web_search", title="B", url_or_doi="https://example.com")
    reduced = reduce_sources([first], [second])
    assert len(reduced) == 1
