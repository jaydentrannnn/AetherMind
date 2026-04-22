"""Guardrails node that validates citations and source policy compliance."""

from __future__ import annotations

from app.agent.state import AgentState
from app.guardrails.citation_verifier import CitationVerifier
from app.guardrails.source_policy import SourcePolicy
from app.llm.router import Router
from app.schemas import GuardrailReport


async def guardrails_node(state: AgentState, *, llm_router: Router | None = None) -> AgentState:
    """Generate guardrail report and preserve in-place citation mutations."""
    draft = state.get("draft")
    if draft is None:
        return {"guardrail_report": GuardrailReport()}

    memory_context = state.get("memory_context", {})
    allow_domains = memory_context.get("allow_domains", [])
    deny_domains = memory_context.get("deny_domains", [])
    _, policy_violations = SourcePolicy.filter_sources(
        state.get("sources", []),
        allow_domains,
        deny_domains,
    )
    verifier = CitationVerifier(llm_router=llm_router)
    report = await verifier.verify(draft, state.get("sources", []))
    report.policy_violations = policy_violations
    return {"guardrail_report": report, "draft": draft}
