"""Memory writer node for final graph step in phase 5."""

from __future__ import annotations

import structlog

from app.agent.state import AgentState
from app.memory import get_memory_service
from app.observability import get_tracer

log = structlog.get_logger(__name__)


async def memory_writer_node(state: AgentState) -> AgentState:
    """Persist the final draft, evidence graph, and critique metadata."""
    trace_id = state.get("trace_id")
    structlog.contextvars.bind_contextvars(
        node="memory_writer", job_id=state.get("job_id"), trace_id=trace_id
    )
    span = get_tracer().span(
        trace_id,
        name="memory_writer",
        input={"topic": state.get("topic"), "approved": state.get("approved", False)},
    )
    try:
        await get_memory_service().write(
            {
                "topic": state.get("topic"),
                "job_id": state.get("job_id"),
                "user_id": state.get("user_id"),
                "trace_id": trace_id,
                "draft": state.get("draft"),
                "findings": state.get("findings", []),
                "sources": state.get("sources", []),
                "critique": state.get("critique"),
                "guardrail_report": state.get("guardrail_report"),
                "feedback": state.get("feedback"),
                "approved": state.get("approved", False),
                "depth": state.get("depth", "standard"),
            }
        )
        get_tracer().end_span(span, output={"persisted": True})
        return {}
    except Exception as exc:
        get_tracer().end_span(span, error=str(exc))
        raise
