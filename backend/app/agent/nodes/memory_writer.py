"""Memory writer node for final graph step in phase 5."""

from __future__ import annotations

from app.agent.state import AgentState
from app.memory import get_memory_service


async def memory_writer_node(state: AgentState) -> AgentState:
    """Persist the final draft, evidence graph, and critique metadata."""
    await get_memory_service().write(
        {
            "topic": state.get("topic"),
            "job_id": state.get("job_id"),
            "user_id": state.get("user_id"),
            "draft": state.get("draft"),
            "findings": state.get("findings", []),
            "sources": state.get("sources", []),
            "critique": state.get("critique"),
            "guardrail_report": state.get("guardrail_report"),
            "feedback": state.get("feedback"),
            "approved": state.get("approved", False),
        }
    )
    return {}
