"""Critic node with revision-loop routing decisions."""

from __future__ import annotations

from app.agent.depth import normalize_depth, profile_for_depth
from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.config import settings
from app.llm.router import Router, router as default_router
from app.schemas import Critique, Report

_STANDARD_PROFILE = profile_for_depth("standard")
SHALLOW_MARKDOWN_MIN_CHARS = _STANDARD_PROFILE.critic_min_markdown_chars
SHALLOW_MIN_SECTIONS = _STANDARD_PROFILE.critic_min_substantive_sections


def _has_evidence_gap(critique: Critique) -> bool:
    """Return true when directives indicate missing evidence collection."""
    return any("evidence" in directive.lower() for directive in critique.directives)


def _has_expand_directive(critique: Critique) -> bool:
    """Return true when directives ask the synthesizer to expand the draft."""
    return any(
        "expand" in directive.lower() or "depth" in directive.lower()
        for directive in critique.directives
    )


def _is_shallow_draft(
    draft: Report | None,
    *,
    min_markdown_chars: int,
    min_substantive_sections: int,
) -> bool:
    """Heuristic: flag drafts that are obviously under-developed."""
    if draft is None:
        return True
    markdown = draft.markdown or ""
    if len(markdown.strip()) < min_markdown_chars:
        return True
    substantive_sections = [s for s in draft.sections if (s.content or "").strip()]
    if len(substantive_sections) < min_substantive_sections:
        return True
    return False


async def critic_node(state: AgentState, *, llm_router: Router | None = None) -> AgentState:
    """Score the draft and choose the next route in the graph loop."""
    selected_router = llm_router or default_router
    depth = normalize_depth(state.get("depth"))
    profile = profile_for_depth(depth)
    revisions = state.get("revisions", 0)
    effective_max_revisions = settings.AGENT_MAX_REVISIONS + profile.extra_revisions
    task = "critic_final" if revisions + 1 >= effective_max_revisions else "critic_inner"
    prompt = renderer.render(
        "critic.j2",
        topic=state["topic"],
        depth=depth,
        draft=state.get("draft"),
        findings=state.get("findings", []),
        guardrail_report=state.get("guardrail_report"),
        revisions=revisions,
        max_revisions=effective_max_revisions,
        min_markdown_chars=profile.critic_min_markdown_chars,
        min_substantive_sections=profile.critic_min_substantive_sections,
    )
    critique = await selected_router.structured(
        task,
        [{"role": "user", "content": prompt}],
        Critique,
    )

    draft = state.get("draft")
    at_max = revisions + 1 >= effective_max_revisions
    shallow = _is_shallow_draft(
        draft,
        min_markdown_chars=profile.critic_min_markdown_chars,
        min_substantive_sections=profile.critic_min_substantive_sections,
    )
    # Only downgrade approval if we still have revisions left to expand; at max
    # revisions the draft finalizes regardless of depth.
    approved = critique.approved and (not shallow or at_max)
    directives = list(critique.directives)
    if (
        shallow
        and not at_max
        and not _has_expand_directive(critique)
        and not _has_evidence_gap(critique)
    ):
        directives.append(
            "expand: draft is too short; expand each section with more "
            "evidence-grounded analysis and add missing sections."
        )

    if approved or at_max:
        next_action = "memory_writer"
    elif _has_evidence_gap(critique):
        next_action = "researcher"
    else:
        next_action = "synthesizer"

    return {
        "depth": depth,
        "critique": critique,
        "approved": approved,
        "revisions": revisions + 1,
        "revision_directives": directives,
        "next_action": next_action,
    }
