"""Tests for citation closure, overlap, and entailment verification paths."""

from __future__ import annotations

from app.guardrails.citation_verifier import CitationVerifier
from app.schemas import (
    Citation,
    Claim,
    EntailmentVerdict,
    Report,
    Section,
    Source,
)


class RaisingRouter:
    """Router stub that fails if entailment fallback is invoked."""

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Raise to prove overlap/closure branches do not call the router."""
        del task, messages, schema, kwargs
        raise AssertionError("router should not be called")


class VerdictRouter:
    """Router stub that returns a configured entailment verdict."""

    def __init__(self, verdict: EntailmentVerdict) -> None:
        """Store verdict used for every structured call."""
        self.verdict = verdict

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Return the configured entailment verdict."""
        del task, messages, schema, kwargs
        return self.verdict


def _draft_with_citation(*, source_id: str, claim_text: str, snippet: str) -> Report:
    """Build a minimal report with one claim and one citation."""
    return Report(
        title="Draft",
        markdown="Body",
        sections=[
            Section(
                title="S1",
                content="C1",
                claims=[Claim(text=claim_text, citations=[Citation(source_id=source_id, snippet=snippet)])],
            )
        ],
    )


async def test_overlap_marks_verified_without_router() -> None:
    """High token overlap should verify citations without entailment fallback."""
    verifier = CitationVerifier(llm_router=RaisingRouter())
    source = Source(source_type="web_search", snippet="alpha beta gamma", url_or_doi="https://example.com")
    draft = _draft_with_citation(source_id=source.id, claim_text="alpha beta gamma", snippet="alpha beta gamma")
    report = await verifier.verify(draft, [source])
    assert report.unverified_claims == []
    assert report.closure_violations == []
    assert draft.sections[0].claims[0].citations[0].verified is True


async def test_entailment_can_verify_low_overlap() -> None:
    """Entailment fallback should verify low-overlap claims on positive verdict."""
    verifier = CitationVerifier(llm_router=VerdictRouter(EntailmentVerdict(entails=True, confidence=0.9)))
    source = Source(source_type="web_search", snippet="source text", url_or_doi="https://example.com")
    draft = _draft_with_citation(source_id=source.id, claim_text="claim text", snippet="different words")
    report = await verifier.verify(draft, [source])
    assert report.unverified_claims == []
    assert draft.sections[0].claims[0].citations[0].verified is True


async def test_refuted_entailment_records_unverified_claim() -> None:
    """Negative entailment verdict should add an unverified claim entry."""
    verifier = CitationVerifier(
        llm_router=VerdictRouter(EntailmentVerdict(entails=False, confidence=0.2, rationale="not supported"))
    )
    source = Source(source_type="web_search", snippet="source text", url_or_doi="https://example.com")
    draft = _draft_with_citation(source_id=source.id, claim_text="claim text", snippet="different words")
    report = await verifier.verify(draft, [source])
    assert len(report.unverified_claims) == 1
    assert report.unverified_claims[0].reason == "llm_refuted"
    assert draft.sections[0].claims[0].citations[0].verified is False


async def test_unknown_source_records_closure_violation() -> None:
    """Unknown citation source ids should be recorded as closure violations."""
    verifier = CitationVerifier(llm_router=RaisingRouter())
    draft = _draft_with_citation(source_id="not-registered", claim_text="claim", snippet="snippet")
    report = await verifier.verify(draft, [])
    assert len(report.closure_violations) == 1
    assert report.closure_violations[0].reason == "unknown_source_id"
    assert draft.sections[0].claims[0].citations[0].verified is False


async def test_verifier_mutates_draft_in_place() -> None:
    """Verifier should flip citation.verified directly on passed draft object."""
    verifier = CitationVerifier(llm_router=RaisingRouter())
    source = Source(source_type="web_search", snippet="alpha beta gamma", url_or_doi="https://example.com")
    draft = _draft_with_citation(source_id=source.id, claim_text="alpha beta gamma", snippet="alpha beta gamma")
    citation = draft.sections[0].claims[0].citations[0]
    assert citation.verified is False
    await verifier.verify(draft, [source])
    assert citation.verified is True
