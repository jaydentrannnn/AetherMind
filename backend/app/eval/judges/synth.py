"""Synthesizer-stage LLM-as-judge wrapper that reuses the report rubric."""

from __future__ import annotations

from app.eval.judge import JudgeRubric, JudgeResult
from app.eval.judges.base import score_with_rubric
from app.llm.router import Router
from app.schemas import Report, Source


def _render(
    topic: str,
    draft: Report,
    sources: list[Source],
    revision_directives: list[str],
) -> str:
    """Build the synth-judge prompt body."""
    sources_blob = (
        "\n".join(f"- {src.id}: {src.title or src.url_or_doi or ''}" for src in sources)
        or "- (none)"
    )
    directives_blob = "\n".join(f"- {d}" for d in revision_directives) or "- (none)"
    return (
        "Evaluate a synthesized research report draft using this rubric (0-5 each): "
        "accuracy, completeness, citation_integrity, bias, structure.\n\n"
        f"Topic: {topic}\n\n"
        f"Title: {draft.title}\n\n"
        f"Summary: {draft.summary or '(none)'}\n\n"
        f"Markdown:\n{draft.markdown[:4000]}\n\n"
        f"Sources:\n{sources_blob}\n\n"
        f"Revision directives:\n{directives_blob}\n\n"
        "Return strict JSON matching the rubric schema."
    )


async def score_synth(
    *,
    topic: str,
    draft: Report,
    sources: list[Source],
    revision_directives: list[str] | None = None,
    llm_router: Router | None = None,
    disabled_reason: str | None = None,
) -> JudgeResult:
    """Score one synthesized report via the ``synth_judge`` task tag."""
    return await score_with_rubric(
        task="synth_judge",
        prompt=_render(topic, draft, sources, revision_directives or []),
        rubric_schema=JudgeRubric,
        aggregate_fields=("accuracy", "completeness", "citation_integrity", "bias", "structure"),
        llm_router=llm_router,
        disabled_reason=disabled_reason,
    )
