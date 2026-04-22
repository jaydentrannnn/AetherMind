"""Pydantic schemas used by the research pipeline and API layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel, Field

SourceType = Literal["web_search", "arxiv", "pdf", "url", "code_exec"]


class Source(BaseModel):
    """Represents a citable source produced by a tool call."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: SourceType
    title: str | None = None
    url_or_doi: str | None = None
    snippet: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """Maps a claim to one registered source identifier."""

    source_id: str
    snippet: str | None = None
    verified: bool = False


class Claim(BaseModel):
    """A report claim and its citation evidence."""

    text: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)


class Section(BaseModel):
    """A named section in a report body."""

    title: str
    content: str
    claims: list[Claim] = Field(default_factory=list)


class Report(BaseModel):
    """A full research report output emitted by synthesis."""

    id: UUID | None = None
    job_id: UUID | None = None
    version: int = 1
    title: str
    summary: str | None = None
    markdown: str
    sections: list[Section] = Field(default_factory=list)
    created_at: datetime | None = None


class SubQuestion(BaseModel):
    """A planner-generated sub-question assigned to researcher nodes."""

    id: str
    question: str
    rationale: str | None = None
    suggested_tools: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    """A researcher output bundle for one sub-question."""

    sub_question_id: str
    answer: str
    evidence: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class Rubric(BaseModel):
    """Scoring rubric used by critic/eval phases."""

    accuracy: int = Field(ge=0, le=5)
    completeness: int = Field(ge=0, le=5)
    citation_integrity: int = Field(ge=0, le=5)
    bias: int = Field(ge=0, le=5)
    structure: int = Field(ge=0, le=5)
    notes: str | None = None


class Critique(BaseModel):
    """Critic feedback over a report draft."""

    score: float = Field(ge=0.0, le=5.0)
    approved: bool
    directives: list[str] = Field(default_factory=list)
    rubric: Rubric | None = None


class Feedback(BaseModel):
    """Human feedback captured after a report is produced."""

    report_id: UUID
    user_comment: str | None = None
    accepted: bool
    created_at: datetime | None = None


class Preference(BaseModel):
    """A stored user preference represented as key/value data."""

    user_id: UUID
    key: str
    value: str
    source: Literal["user", "inferred"] = "user"


class ToolResult(BaseModel):
    """Standard output contract for all research tools."""

    content: str
    source: Source


class PreferenceDelta(BaseModel):
    """A structured preference update extracted from feedback text."""

    key: str
    value: str
    rationale: str | None = None


class PreferenceDeltaList(BaseModel):
    """Container for LLM-extracted preference updates."""

    deltas: list[PreferenceDelta] = Field(default_factory=list)


class RecalledMemory(BaseModel):
    """Normalized memory payload returned by the planner recall call."""

    preferences: dict[str, str] = Field(default_factory=dict)
    allow_domains: list[str] = Field(default_factory=list)
    deny_domains: list[str] = Field(default_factory=list)
    past_reports: list[dict[str, Any]] = Field(default_factory=list)
    semantic_preferences: list[dict[str, Any]] = Field(default_factory=list)


class EntailmentVerdict(BaseModel):
    """Model verdict for whether source evidence entails a claim."""

    entails: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None


class UnverifiedClaim(BaseModel):
    """Claim/citation pair that failed one or more guardrail checks."""

    claim_text: str
    source_id: str | None
    reason: Literal["low_overlap", "llm_refuted", "unknown_source_id"]
    rationale: str | None = None


class PolicyViolation(BaseModel):
    """A source URL that violates allow/deny policy constraints."""

    source_id: str
    url: str | None
    reason: Literal["deny_match", "not_in_allow", "invalid_url"]


class GuardrailReport(BaseModel):
    """Aggregated output from guardrail validation over a draft report."""

    unverified_claims: list[UnverifiedClaim] = Field(default_factory=list)
    closure_violations: list[UnverifiedClaim] = Field(default_factory=list)
    policy_violations: list[PolicyViolation] = Field(default_factory=list)
