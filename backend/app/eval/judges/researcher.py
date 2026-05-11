"""Researcher-stage LLM-as-judge rubric for evidence quality."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.eval.judge import JudgeResult
from app.eval.judges.base import score_with_rubric
from app.llm.router import Router
from app.schemas import Finding, Source, SubQuestion


class ResearcherJudgeRubric(BaseModel):
    """0-5 rubric for one researcher finding."""

    evidence_quality: int = Field(ge=0, le=5)
    relevance: int = Field(ge=0, le=5)
    source_grounding: int = Field(ge=0, le=5)
    reasoning: str = ""


def _render(sub_question: SubQuestion, finding: Finding, sources: list[Source]) -> str:
    """Build the researcher-judge prompt body."""
    sources_blob = (
        "\n".join(
            f"- {src.id}: {src.title or src.url_or_doi or ''} :: {src.snippet or ''}"
            for src in sources
        )
        or "- (no sources)"
    )
    return (
        "Evaluate a researcher's finding for one sub-question.\n"
        "Score each dimension 0-5: evidence_quality (do the evidence lines support "
        "the answer?), relevance (does the answer actually address the question?), "
        "source_grounding (are the cited source ids backed by content snippets?).\n\n"
        f"Sub-question: {sub_question.question}\n\n"
        f"Answer:\n{finding.answer}\n\n"
        f"Evidence lines:\n{chr(10).join('- ' + e for e in finding.evidence) or '- (none)'}\n\n"
        f"Cited source ids: {finding.source_ids}\n\n"
        f"Sources:\n{sources_blob}\n\n"
        "Return strict JSON matching the rubric schema."
    )


async def score_finding(
    *,
    sub_question: SubQuestion,
    finding: Finding,
    sources: list[Source],
    llm_router: Router | None = None,
    disabled_reason: str | None = None,
) -> JudgeResult:
    """Score one researcher finding via the ``researcher_judge`` task tag."""
    return await score_with_rubric(
        task="researcher_judge",
        prompt=_render(sub_question, finding, sources),
        rubric_schema=ResearcherJudgeRubric,
        aggregate_fields=("evidence_quality", "relevance", "source_grounding"),
        llm_router=llm_router,
        disabled_reason=disabled_reason,
    )
