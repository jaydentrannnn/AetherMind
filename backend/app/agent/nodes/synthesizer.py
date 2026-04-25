"""Synthesizer node for producing structured report drafts."""

from __future__ import annotations

from app.agent.depth import normalize_depth, profile_for_depth
from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.llm.router import Router, router as default_router
from app.schemas import Report

SYNTH_MAX_TOKENS = 16384


async def synthesizer_node(
    state: AgentState, *, llm_router: Router | None = None
) -> AgentState:
    """Generate a draft report from findings and optional revision directives."""
    selected_router = llm_router or default_router
    depth = normalize_depth(state.get("depth"))
    profile = profile_for_depth(depth)
    sources = state.get("filtered_sources") or state.get("sources", [])
    prompt = renderer.render(
        "synthesizer.j2",
        topic=state["topic"],
        depth=depth,
        target_sections_min=profile.synth_target_sections_min,
        target_sections_max=profile.synth_target_sections_max,
        findings=state.get("findings", []),
        sources=sources,
        valid_source_ids=[s.id for s in sources],
        revision_directives=state.get("revision_directives", []),
    )
    report = await selected_router.structured(
        "synthesize",
        [{"role": "user", "content": prompt}],
        Report,
        max_tokens=SYNTH_MAX_TOKENS,
    )
    return {"draft": report}
