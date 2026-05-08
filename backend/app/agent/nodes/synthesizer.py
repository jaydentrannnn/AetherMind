"""Synthesizer node for producing structured report drafts."""

from __future__ import annotations

import structlog

from app.agent.depth import normalize_depth, profile_for_depth
from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.llm.router import Router, router as default_router
from app.observability import get_tracer
from app.schemas import Report

log = structlog.get_logger(__name__)

SYNTH_MAX_TOKENS = 16384


async def synthesizer_node(
    state: AgentState, *, llm_router: Router | None = None
) -> AgentState:
    """Generate a draft report from findings and optional revision directives."""
    trace_id = state.get("trace_id")
    job_id = state.get("job_id")
    structlog.contextvars.bind_contextvars(
        node="synthesizer", job_id=job_id, trace_id=trace_id
    )
    span = get_tracer().span(trace_id, name="synthesizer", input={"topic": state.get("topic")})
    try:
        selected_router = llm_router or default_router
        depth = normalize_depth(state.get("depth"))
        profile = profile_for_depth(depth)
        sources = state.get("filtered_sources") or state.get("sources", [])
        alias_map: dict[str, str] = {}
        for source in sources:
            alias_ids = (getattr(source, "metadata", None) or {}).get("alias_ids") or []
            for alias_id in alias_ids:
                alias_map[str(alias_id)] = source.id
        findings = state.get("findings", [])
        findings_for_prompt = []
        for finding in findings:
            remapped = [alias_map.get(source_id, source_id) for source_id in finding.source_ids]
            findings_for_prompt.append(finding.model_copy(update={"source_ids": remapped}))
        prompt = renderer.render(
            "synthesizer.j2",
            topic=state["topic"],
            depth=depth,
            target_sections_min=profile.synth_target_sections_min,
            target_sections_max=profile.synth_target_sections_max,
            findings=findings_for_prompt,
            sources=sources,
            valid_source_ids=[s.id for s in sources],
            revision_directives=state.get("revision_directives", []),
        )
        report = await selected_router.structured(
            "synthesize",
            [{"role": "user", "content": prompt}],
            Report,
            max_tokens=SYNTH_MAX_TOKENS,
            metadata={"trace_id": trace_id, "job_id": job_id, "node": "synthesizer"},
        )
        get_tracer().end_span(span, output={"sections": len(report.sections)})
        return {"draft": report}
    except Exception as exc:
        get_tracer().end_span(span, error=str(exc))
        raise
