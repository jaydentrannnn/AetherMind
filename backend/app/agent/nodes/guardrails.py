"""Guardrails node that validates citations and source policy compliance."""

from __future__ import annotations

import structlog

from app.agent.state import AgentState
from app.guardrails.citation_verifier import CitationVerifier
from app.guardrails.source_policy import SourcePolicy
from app.llm.router import Router
from app.observability import get_tracer
from app.schemas import GuardrailReport

log = structlog.get_logger(__name__)


async def guardrails_node(state: AgentState, *, llm_router: Router | None = None) -> AgentState:
    """Generate guardrail report and preserve in-place citation mutations."""
    trace_id = state.get("trace_id")
    structlog.contextvars.bind_contextvars(
        node="guardrails", job_id=state.get("job_id"), trace_id=trace_id
    )
    span = get_tracer().span(trace_id, name="guardrails", input={"has_draft": state.get("draft") is not None})
    try:
        draft = state.get("draft")
        if draft is None:
            get_tracer().end_span(span, output={"skipped": True})
            return {"guardrail_report": GuardrailReport()}

        memory_context = state.get("memory_context", {})
        allow_domains = memory_context.get("allow_domains", [])
        deny_domains = memory_context.get("deny_domains", [])
        allowed_sources, policy_violations = SourcePolicy.filter_sources(
            state.get("sources", []),
            allow_domains,
            deny_domains,
        )
        verifier = CitationVerifier(llm_router=llm_router)
        report = await verifier.verify(draft, allowed_sources)
        report.policy_violations = policy_violations
        get_tracer().end_span(span, output={"violations": len(policy_violations)})
        return {"guardrail_report": report, "draft": draft, "filtered_sources": allowed_sources}
    except Exception as exc:
        get_tracer().end_span(span, error=str(exc))
        raise
