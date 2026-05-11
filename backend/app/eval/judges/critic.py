"""Critic-stage LLM-as-judge for rubric stability and directive quality."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.eval.judge import JudgeResult
from app.eval.judges.base import score_with_rubric
from app.llm.router import Router
from app.schemas import Critique, Report


class CriticJudgeRubric(BaseModel):
    """0-5 rubric for critic output quality."""

    rubric_calibration: int = Field(ge=0, le=5)
    directive_actionability: int = Field(ge=0, le=5)
    consistency: int = Field(ge=0, le=5)
    reasoning: str = ""


def _render(draft: Report | None, critique: Critique) -> str:
    """Build the critic-judge prompt body."""
    draft_markdown = (draft.markdown[:2000] if draft and draft.markdown else "(no draft)")
    directives = "\n".join(f"- {d}" for d in critique.directives) or "- (none)"
    return (
        "Evaluate a critic's review of a draft research report.\n"
        "Score 0-5: rubric_calibration (are the rubric scores reasonable for the "
        "draft?), directive_actionability (are the directives specific and "
        "implementable?), consistency (does approved match the score and "
        "directives?).\n\n"
        f"Draft markdown (truncated):\n{draft_markdown}\n\n"
        f"Critic score: {critique.score}\n"
        f"Critic approved: {critique.approved}\n"
        f"Directives:\n{directives}\n\n"
        "Return strict JSON matching the rubric schema."
    )


async def score_critic(
    *,
    draft: Report | None,
    critique: Critique,
    llm_router: Router | None = None,
    disabled_reason: str | None = None,
) -> JudgeResult:
    """Score one critic output via the ``critic_judge`` task tag."""
    return await score_with_rubric(
        task="critic_judge",
        prompt=_render(draft, critique),
        rubric_schema=CriticJudgeRubric,
        aggregate_fields=("rubric_calibration", "directive_actionability", "consistency"),
        llm_router=llm_router,
        disabled_reason=disabled_reason,
    )
