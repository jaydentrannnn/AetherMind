"""Planner node implementation for LangGraph phase-5 flow."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.depth import DepthLevel, normalize_depth, profile_for_depth
from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.llm.router import Router, router as default_router
from app.memory import get_memory_service
from app.schemas import SubQuestion


class PlannerOutput(BaseModel):
    """Structured planner output used to seed researcher fan-out."""

    sub_questions: list[SubQuestion] = Field(default_factory=list)


def _clamp_sub_questions(sub_questions: list[SubQuestion], depth: DepthLevel) -> list[SubQuestion]:
    """Deterministically clamp planner output to the profile's max question budget."""
    max_questions = profile_for_depth(depth).planner_max_subquestions
    if len(sub_questions) <= max_questions:
        return sub_questions
    return sub_questions[:max_questions]


async def planner_node(
    state: AgentState, *, llm_router: Router | None = None
) -> AgentState:
    """Plan sub-questions for the topic and hydrate memory context."""
    selected_router = llm_router or default_router
    topic = state["topic"]
    depth = normalize_depth(state.get("depth"))
    depth_profile = profile_for_depth(depth)
    preferences = state.get("preferences", {})
    memory_context = await get_memory_service().recall(topic)
    prompt = renderer.render(
        "planner.j2",
        topic=topic,
        depth=depth,
        planner_min_subquestions=depth_profile.planner_min_subquestions,
        planner_max_subquestions=depth_profile.planner_max_subquestions,
        preferences=preferences,
        memory_context=memory_context,
    )
    planned = await selected_router.structured(
        "planner",
        [{"role": "user", "content": prompt}],
        PlannerOutput,
    )
    return {
        "depth": depth,
        "preferences": preferences,
        "memory_context": memory_context,
        "plan": _clamp_sub_questions(planned.sub_questions, depth),
        "revisions": state.get("revisions", 0),
        "approved": state.get("approved", False),
    }
