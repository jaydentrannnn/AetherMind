"""Guardrail exports for citation verification and source policy checks."""

from app.guardrails.citation_verifier import CitationVerifier
from app.guardrails.source_policy import SourcePolicy
from app.schemas import GuardrailReport


async def guardrails_node(*args, **kwargs):  # noqa: ANN002, ANN003
    """Lazily proxy to the node implementation to avoid import cycles."""
    from app.agent.nodes.guardrails import guardrails_node as _guardrails_node

    return await _guardrails_node(*args, **kwargs)


__all__ = ["CitationVerifier", "SourcePolicy", "guardrails_node", "GuardrailReport"]
