"""Shared LangGraph state and reducer helpers for the agent loop."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from app.agent.depth import DepthLevel
from app.schemas import Critique, Feedback, GuardrailReport, Finding, Report, Source, SubQuestion


def reduce_findings(existing: list[Finding], incoming: list[Finding]) -> list[Finding]:
    """Merge findings by sub-question id, preferring the latest result."""
    merged: dict[str, Finding] = {item.sub_question_id: item for item in existing}
    for item in incoming:
        merged[item.sub_question_id] = item
    return list(merged.values())


def reduce_sources(existing: list[Source], incoming: list[Source]) -> list[Source]:
    """Merge sources while deduping by URL/DOI when available."""
    merged: dict[str, Source] = {}
    for source in [*existing, *incoming]:
        dedupe_key = source.url_or_doi or source.id
        if dedupe_key not in merged:
            merged[dedupe_key] = source
    return list(merged.values())


class AgentState(TypedDict, total=False):
    """Top-level state for the planner -> researcher -> synth loop."""

    topic: str
    depth: DepthLevel
    preferences: dict[str, Any]
    memory_context: dict[str, Any]
    user_id: str
    job_id: str
    plan: list[SubQuestion]
    sub_question: SubQuestion
    findings: Annotated[list[Finding], reduce_findings]
    sources: Annotated[list[Source], reduce_sources]
    draft: Report | None
    critique: Critique | None
    guardrail_report: GuardrailReport | None
    feedback: Feedback | None
    revisions: int
    approved: bool
    next_action: str
    revision_directives: list[str]
    filtered_sources: list[Source] | None
