"""Planner node implementation for LangGraph phase-5 flow."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.llm.router import Router, router as default_router
from app.memory import get_memory_service
from app.schemas import SubQuestion


class PlannerOutput(BaseModel):
    """Structured planner output used to seed researcher fan-out."""

    sub_questions: list[SubQuestion] = Field(default_factory=list)


async def planner_node(
    state: AgentState, *, llm_router: Router | None = None
) -> AgentState:
    """Plan sub-questions for the topic and hydrate memory context."""
    selected_router = llm_router or default_router
    topic = state["topic"]
    preferences = state.get("preferences", {})
    memory_context = await get_memory_service().recall(topic)
    prompt = renderer.render(
        "planner.j2",
        topic=topic,
        preferences=preferences,
        memory_context=memory_context,
    )
    planned = await selected_router.structured(
        "planner",
        [{"role": "user", "content": prompt}],
        PlannerOutput,
    )
    return {
        "preferences": preferences,
        "memory_context": memory_context,
        "plan": planned.sub_questions,
        "revisions": state.get("revisions", 0),
        "approved": state.get("approved", False),
    }
