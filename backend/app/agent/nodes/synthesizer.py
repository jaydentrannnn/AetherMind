"""Synthesizer node for producing structured report drafts."""

from __future__ import annotations

from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.llm.router import Router, router as default_router
from app.schemas import Report


async def synthesizer_node(
    state: AgentState, *, llm_router: Router | None = None
) -> AgentState:
    """Generate a draft report from findings and optional revision directives."""
    selected_router = llm_router or default_router
    prompt = renderer.render(
        "synthesizer.j2",
        topic=state["topic"],
        findings=state.get("findings", []),
        sources=state.get("sources", []),
        revision_directives=state.get("revision_directives", []),
    )
    report = await selected_router.structured(
        "synthesize",
        [{"role": "user", "content": prompt}],
        Report,
    )
    return {"draft": report}
