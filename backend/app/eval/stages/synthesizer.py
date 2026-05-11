"""Synthesizer-stage eval: citation closure, directive coverage, judge."""

from __future__ import annotations

from typing import Any

from app.agent.depth import normalize_depth, profile_for_depth
from app.agent.nodes.synthesizer import synthesizer_node
from app.eval.judges import score_synth
from app.eval.metrics import answer_relevance, citation_precision, faithfulness
from app.eval.models import EvalCitation, EvalMetrics, StageCaseResult, StageReport
from app.eval.stages._common import build_stage_report, load_stage_fixtures, tokenize
from app.llm.router import TaskTag
from app.schemas import Citation, Claim, Finding, Report, Section, Source


class _MockSynthRouter:
    """Deterministic router stub for synthesizer-stage --mock-llm mode.

    Builds a minimal valid Report from the provided findings and sources, citing
    every source by id so citation-closure checks pass without an LLM call.
    """

    def __init__(
        self,
        *,
        topic: str,
        depth: str,
        sources: list[Source],
        findings: list[Finding],
        revision_directives: list[str] | None = None,
    ) -> None:
        """Cache inputs needed to assemble a deterministic Report."""
        self._topic = topic
        self._depth = depth
        self._sources = sources
        self._findings = findings
        self._directives = revision_directives or []

    async def structured(self, task: TaskTag, messages: list[dict[str, Any]], schema, **kwargs):
        """Return a hand-built Report shaped for synth-stage closure checks."""
        del messages, kwargs
        if task != "synthesize":
            raise AssertionError(f"_MockSynthRouter only handles 'synthesize', got {task!r}")
        if schema is not Report:
            raise AssertionError(f"_MockSynthRouter expects Report, got {schema!r}")
        profile = profile_for_depth(self._depth)
        sections: list[Section] = []
        # Pad to the minimum substantive section count so critic-style shallow
        # checks (when synth output flows downstream) do not flag the mock.
        target_sections = max(profile.synth_target_sections_min, len(self._findings) or 1)
        for idx in range(target_sections):
            finding = self._findings[idx] if idx < len(self._findings) else None
            source = self._sources[idx % len(self._sources)] if self._sources else None
            citation_list = (
                [Citation(source_id=source.id, snippet=source.snippet or "")] if source else []
            )
            claim_text = (finding.answer if finding else f"Mock claim {idx + 1} for {self._topic}.")
            sections.append(
                Section(
                    title=f"Mock section {idx + 1}",
                    content=claim_text + " " + (source.snippet or "" if source else ""),
                    claims=[Claim(text=claim_text, confidence=0.5, citations=citation_list)],
                )
            )
        markdown_body = "\n\n".join(f"## {s.title}\n\n{s.content}" for s in sections)
        if self._directives:
            # Surface the directive text verbatim in the body so the directive-
            # coverage check has a chance to find the keywords; the real LLM
            # would normally do this implicitly by addressing the directives.
            markdown_body += "\n\n## Revision notes\n\n" + "\n".join(
                f"- {d}" for d in self._directives
            )
        return Report(
            title=f"Mock report on {self._topic}",
            summary="Deterministic mock summary for --mock-llm eval.",
            markdown=markdown_body,
            sections=sections,
        )


def _citation_closure_ok(draft: Report, valid_ids: set[str]) -> tuple[bool, list[str]]:
    """Return (ok, unknown_ids) for closure checks on the synth output."""
    unknown: set[str] = set()
    for section in draft.sections:
        for claim in section.claims:
            for citation in claim.citations:
                if citation.source_id not in valid_ids:
                    unknown.add(citation.source_id)
    return (not unknown), sorted(unknown)


def _directive_coverage(draft: Report, keywords: list[str]) -> tuple[float, list[str]]:
    """Return (coverage_ratio, missing_keywords) by token overlap on markdown."""
    if not keywords:
        return 1.0, []
    body_tokens = tokenize(draft.markdown)
    missing = [kw for kw in keywords if not body_tokens & tokenize(kw)]
    coverage = round(1 - len(missing) / len(keywords), 4)
    return coverage, missing


def _compute_real_context_metrics(draft: Report, findings: list[Finding], sources: list[Source]) -> EvalMetrics:
    """Compute Ragas-style metrics with contexts derived from real findings/sources.

    Unlike the legacy fixture path which uses hand-written `contexts`, here we
    construct contexts from the actual evidence the synthesizer was given so
    the score reflects pipeline behavior end-to-end.
    """
    contexts = [
        evidence_line
        for finding in findings
        for evidence_line in (finding.evidence or [finding.answer])
    ]
    contexts.extend(src.snippet for src in sources if src.snippet)

    # Use the markdown as the answer and the topic-like first-section title as
    # the question proxy when no explicit question is supplied.
    question_proxy = draft.title
    fixture_citations = [
        EvalCitation(source_id=src.id, snippet=src.snippet or "")
        for src in sources
    ]
    return EvalMetrics(
        faithfulness=faithfulness(question_proxy, draft.markdown, contexts),
        answer_relevance=answer_relevance(question_proxy, draft.markdown),
        citation_precision=citation_precision(draft.markdown, fixture_citations),
    )


async def run_synth_stage(
    *,
    mock_llm: bool = False,
    deterministic_only: bool = False,
) -> StageReport:
    """Evaluate the synthesizer node for citation closure and directive coverage.

    Args:
        mock_llm: When True, swap the synth's LLM call for a deterministic
            Report constructed from the fixture sources/findings.
        deterministic_only: When True, skip the synth_judge LLM call.
    """
    cases = load_stage_fixtures("synthesizer")
    results: list[StageCaseResult] = []

    for case in cases:
        case_id = case["case_id"]
        topic = case["topic"]
        depth = normalize_depth(case.get("depth"))
        sources = [Source.model_validate(s) for s in case.get("sources", [])]
        findings = [Finding.model_validate(f) for f in case.get("findings", [])]
        directives = case.get("revision_directives", [])
        expected = case.get("expected", {})
        directive_keywords = expected.get("directive_keywords", [])

        state_in = {
            "topic": topic,
            "depth": depth,
            "findings": findings,
            "sources": sources,
            "filtered_sources": sources,
            "revision_directives": directives,
        }

        try:
            llm_router = (
                _MockSynthRouter(
                    topic=topic,
                    depth=depth,
                    sources=sources,
                    findings=findings,
                    revision_directives=directives,
                )
                if mock_llm
                else None
            )
            state_out = await synthesizer_node(state_in, llm_router=llm_router)  # type: ignore[arg-type]
            draft = state_out.get("draft")
            if draft is None:
                raise RuntimeError("synthesizer returned no draft")
        except Exception as exc:
            results.append(
                StageCaseResult(
                    case_id=case_id,
                    passed=False,
                    deterministic={"error": True},
                    diagnostics=[f"synthesizer_node raised: {exc!r}"],
                    judge=None,
                )
            )
            continue

        valid_ids = {src.id for src in sources}
        closure_ok, unknown_ids = _citation_closure_ok(draft, valid_ids)
        coverage, missing = _directive_coverage(draft, directive_keywords)
        metrics_obj = _compute_real_context_metrics(draft, findings, sources)

        diagnostics: list[str] = []
        if not closure_ok:
            diagnostics.append(f"unknown citation source ids: {unknown_ids}")
        if missing:
            diagnostics.append(f"revision directives not covered: {missing}")

        deterministic: dict[str, Any] = {
            "citation_closure_ok": closure_ok,
            "unknown_source_ids": unknown_ids,
            "directive_coverage": coverage,
            "directive_missing": missing,
            "faithfulness": metrics_obj.faithfulness,
            "answer_relevance": metrics_obj.answer_relevance,
            "citation_precision": metrics_obj.citation_precision,
        }

        judge_result = None
        if not mock_llm:
            judge_result = await score_synth(
                topic=topic,
                draft=draft,
                sources=sources,
                revision_directives=directives,
                disabled_reason=(
                    "deterministic_only enabled" if deterministic_only else None
                ),
            )

        results.append(
            StageCaseResult(
                case_id=case_id,
                passed=(not diagnostics),
                deterministic=deterministic,
                diagnostics=diagnostics,
                judge=judge_result,
            )
        )

    return build_stage_report(
        stage="synthesizer",
        results=results,
        deterministic_only=deterministic_only or mock_llm,
    )
