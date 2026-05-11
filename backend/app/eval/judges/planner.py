"""Planner-stage LLM-as-judge rubric and prompt rendering."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.eval.judge import JudgeResult
from app.eval.judges.base import score_with_rubric
from app.llm.router import Router
from app.schemas import SubQuestion


class PlannerJudgeRubric(BaseModel):
    """0-5 rubric for planner output quality."""

    coverage: int = Field(ge=0, le=5)
    decomposition: int = Field(ge=0, le=5)
    depth_appropriateness: int = Field(ge=0, le=5)
    memory_use: int = Field(ge=0, le=5)
    reasoning: str = ""


def _render(topic: str, depth: str, plan: list[SubQuestion], memory_context: dict | None) -> str:
    """Build the planner-judge prompt body."""
    plan_blob = "\n".join(f"- ({sq.id}) {sq.question}" for sq in plan) or "- (empty plan)"
    memory_blob = (
        "\n".join(f"- {k}: {v}" for k, v in (memory_context or {}).items()) or "- (none)"
    )
    return (
        "Evaluate a research planner's sub-question decomposition.\n"
        "Score each dimension 0-5: coverage (does the plan cover the topic?), "
        "decomposition (are sub-questions distinct and well-formed?), "
        "depth_appropriateness (right granularity for the depth tier?), "
        "memory_use (does it leverage memory context when present?).\n\n"
        f"Topic: {topic}\n"
        f"Depth: {depth}\n\n"
        f"Plan:\n{plan_blob}\n\n"
        f"Memory context:\n{memory_blob}\n\n"
        "Return strict JSON matching the rubric schema."
    )


async def score_plan(
    *,
    topic: str,
    depth: str,
    plan: list[SubQuestion],
    memory_context: dict | None = None,
    llm_router: Router | None = None,
    disabled_reason: str | None = None,
) -> JudgeResult:
    """Score one planner output via the ``planner_judge`` task tag."""
    return await score_with_rubric(
        task="planner_judge",
        prompt=_render(topic, depth, plan, memory_context),
        rubric_schema=PlannerJudgeRubric,
        aggregate_fields=("coverage", "decomposition", "depth_appropriateness", "memory_use"),
        llm_router=llm_router,
        disabled_reason=disabled_reason,
    )
