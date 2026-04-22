"""Citation closure and verification checks for synthesized reports."""

from __future__ import annotations

import re

from app.config import settings
from app.llm.router import Router, router as default_router
from app.schemas import EntailmentVerdict, GuardrailReport, Report, Source, UnverifiedClaim


class CitationVerifier:
    """Verify report citations via closure, overlap, and entailment checks."""

    def __init__(self, *, llm_router: Router | None = None) -> None:
        """Store a router instance used for entailment fallback calls."""
        self._router = llm_router or default_router

    @staticmethod
    def _tokenize(text: str | None) -> set[str]:
        """Tokenize text into lowercase alphanumeric units for overlap checks."""
        if not text:
            return set()
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    @classmethod
    def _jaccard(cls, left: str | None, right: str | None) -> float:
        """Compute Jaccard overlap between two text strings."""
        left_tokens = cls._tokenize(left)
        right_tokens = cls._tokenize(right)
        if not left_tokens or not right_tokens:
            return 0.0
        union = left_tokens | right_tokens
        if not union:
            return 0.0
        return len(left_tokens & right_tokens) / len(union)

    async def verify(self, draft: Report, sources: list[Source]) -> GuardrailReport:
        """Mutate citation verification flags and return guardrail findings."""
        source_map = {source.id: source for source in sources}
        report = GuardrailReport()

        # Phase 6 ships overlap + router entailment only.
        # Local NLI cross-encoder is deferred to a later embeddings/routing addition.
        for section in draft.sections:
            for claim in section.claims:
                for citation in claim.citations:
                    source = source_map.get(citation.source_id)
                    if source is None:
                        citation.verified = False
                        report.closure_violations.append(
                            UnverifiedClaim(
                                claim_text=claim.text,
                                source_id=citation.source_id,
                                reason="unknown_source_id",
                            )
                        )
                        continue

                    candidate_snippet = citation.snippet or source.snippet or ""
                    overlap = self._jaccard(claim.text, candidate_snippet)
                    if overlap >= settings.CITATION_OVERLAP_THRESHOLD:
                        citation.verified = True
                        continue

                    verdict = await self._router.structured(
                        "entailment",
                        [
                            {
                                "role": "user",
                                "content": (
                                    "Does the evidence entail the claim?\n"
                                    f"Claim: {claim.text}\n"
                                    f"Evidence: {candidate_snippet}"
                                ),
                            }
                        ],
                        EntailmentVerdict,
                    )
                    if verdict.entails and verdict.confidence >= settings.CITATION_ENTAILMENT_MIN_CONFIDENCE:
                        citation.verified = True
                        continue

                    citation.verified = False
                    report.unverified_claims.append(
                        UnverifiedClaim(
                            claim_text=claim.text,
                            source_id=citation.source_id,
                            reason="llm_refuted",
                            rationale=verdict.rationale,
                        )
                    )

        return report
# NLI / entailment + heuristics — guardrails (plan §7).
