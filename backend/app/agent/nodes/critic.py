"""Critic node with revision-loop routing decisions."""

from __future__ import annotations

from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.config import settings
from app.llm.router import Router, router as default_router
from app.schemas import Critique


def _has_evidence_gap(critique: Critique) -> bool:
    """Return true when directives indicate missing evidence collection."""
    return any("evidence" in directive.lower() for directive in critique.directives)


async def critic_node(state: AgentState, *, llm_router: Router | None = None) -> AgentState:
    """Score the draft and choose the next route in the graph loop."""
    selected_router = llm_router or default_router
    revisions = state.get("revisions", 0)
    max_revisions = settings.AGENT_MAX_REVISIONS
    task = "critic_final" if revisions + 1 >= max_revisions else "critic_inner"
    prompt = renderer.render(
        "critic.j2",
        topic=state["topic"],
        draft=state.get("draft"),
        findings=state.get("findings", []),
        guardrail_report=state.get("guardrail_report"),
        revisions=revisions,
        max_revisions=max_revisions,
    )
    critique = await selected_router.structured(
        task,
        [{"role": "user", "content": prompt}],
        Critique,
    )

    if critique.approved or revisions + 1 >= max_revisions:
        next_action = "memory_writer"
    elif _has_evidence_gap(critique):
        next_action = "researcher"
    else:
        next_action = "synthesizer"

    return {
        "critique": critique,
        "approved": critique.approved,
        "revisions": revisions + 1,
        "revision_directives": critique.directives,
        "next_action": next_action,
    }
