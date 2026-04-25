"""Pure transform helpers for adapting backend models to UI response shapes."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.models import Report as ReportEntity
from app.models import ResearchJob
from app.schemas import GuardrailReport, Rubric, Source, UnverifiedClaim

DOI_PATTERN = re.compile(
    r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/\S+)$",
    re.IGNORECASE,
)


def _normalize_source_url(url_or_doi: str | None) -> str:
    """Normalize persisted source links into frontend-clickable URLs when possible."""
    raw = (url_or_doi or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        return raw
    lower = raw.lower()
    if lower.startswith(("doi.org/", "dx.doi.org/")):
        return f"https://{raw}"
    doi_match = DOI_PATTERN.match(raw)
    if doi_match:
        return f"https://doi.org/{doi_match.group(1)}"
    if raw.startswith("www."):
        return f"https://{raw}"
    return raw


def _domain_from_url(url: str | None) -> str:
    """Extract a lowercased hostname from a URL-like source string."""
    if not url:
        return ""
    return (urlparse(url).hostname or "").lower()


def _map_source_type(source_type: str) -> str:
    """Map backend source type names to UI enum values."""
    mapping = {
        "web_search": "web",
        "code_exec": "code",
    }
    return mapping.get(source_type, source_type)


def _source_display_title(source: Source, url: str) -> str:
    """Derive a user-friendly source title when tool metadata is sparse."""
    title = (source.title or "").strip()
    if title and title.lower() != "untitled source":
        return title
    domain = _domain_from_url(url)
    if domain:
        return domain
    if url:
        return url
    return f"Source {source.id[:8]}"


def source_to_ui(source: Source, *, verified: bool = False) -> dict:
    """Convert one backend Source into the frontend source card shape."""
    url = _normalize_source_url(source.url_or_doi)
    domain = _domain_from_url(url)
    return {
        "id": source.id,
        "title": _source_display_title(source, url),
        "url": url,
        "domain": domain,
        "snippet": source.snippet,
        "verified": verified,
        "type": _map_source_type(source.source_type),
    }


def guardrail_violation_to_ui(claim: UnverifiedClaim) -> dict:
    """Convert one guardrail violation record into the frontend list shape."""
    return {
        "claim": claim.claim_text,
        "rationale": claim.rationale or claim.reason,
        "source_ids": [claim.source_id] if claim.source_id else [],
    }


def guardrail_to_ui(guardrails: GuardrailReport | None) -> dict:
    """Convert backend GuardrailReport into the UI-compatible structure."""
    if guardrails is None:
        return {
            "unverified_claims": [],
            "policy_violations": [],
            "closure_violations": [],
        }
    return {
        "unverified_claims": [
            guardrail_violation_to_ui(item) for item in guardrails.unverified_claims
        ],
        "policy_violations": [
            {
                "claim": violation.url or "policy violation",
                "rationale": violation.reason,
                "source_ids": [violation.source_id],
            }
            for violation in guardrails.policy_violations
        ],
        "closure_violations": [
            guardrail_violation_to_ui(item) for item in guardrails.closure_violations
        ],
    }


def rubric_to_ui(rubric: Rubric | None) -> dict:
    """Convert the flat backend Rubric fields into UI score dimensions."""
    if rubric is None:
        return {}
    return {
        "accuracy": {"score": rubric.accuracy, "max": 5, "label": "Accuracy"},
        "completeness": {"score": rubric.completeness, "max": 5, "label": "Completeness"},
        "citation_integrity": {
            "score": rubric.citation_integrity,
            "max": 5,
            "label": "Citation integrity",
        },
        "bias": {"score": rubric.bias, "max": 5, "label": "Bias"},
        "structure": {
            "score": rubric.structure,
            "max": 5,
            "label": "Structure",
            "rationale": rubric.notes,
        },
    }


def research_job_summary_to_ui(*, job: ResearchJob, latest_report_id: str | None) -> dict:
    """Shape one research job row plus optional latest report id for the reports index."""
    return {
        "job_id": job.id,
        "topic": job.topic,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "latest_report_id": latest_report_id,
    }


def version_to_ui(report_row: ReportEntity) -> dict:
    """Map one report ORM row to the frontend version metadata shape."""
    return {
        "id": report_row.id,
        "created_at": report_row.created_at.isoformat() if report_row.created_at else "",
        "label": f"v{report_row.version}",
        "summary_diff": None,
    }


def _section_blocks_from_markdown(markdown: str) -> list[dict]:
    """Provide a minimal section fallback when structured sections are unavailable."""
    return [{"id": "section-1", "title": "Report", "content": [{"type": "p", "text": markdown}]}]


def report_to_response(
    *,
    report_row: ReportEntity,
    sources: list[Source],
    guardrails: GuardrailReport | None,
    rubric: Rubric | None,
    trace_id: str | None,
    request_id: str | None,
    depth: str = "standard",
    verified_source_ids: set[str] | None = None,
) -> dict:
    """Assemble the frontend report payload from persisted backend fragments."""
    verified_ids = verified_source_ids or set()
    payload = report_row.json_blob or {}
    markdown = payload.get("markdown") or report_row.markdown
    sections = payload.get("sections")
    if not sections:
        sections = _section_blocks_from_markdown(markdown)
    return {
        "id": report_row.id,
        "job_id": report_row.job_id,
        "title": payload.get("title") or "Untitled report",
        "summary": payload.get("summary"),
        "markdown": markdown,
        "sections": sections,
        "sources": [
            source_to_ui(source, verified=source.id in verified_ids) for source in sources
        ],
        "guardrails": guardrail_to_ui(guardrails),
        "rubric": rubric_to_ui(rubric),
        "versions": [],
        "depth": depth,
        "created_at": report_row.created_at.isoformat() if report_row.created_at else "",
        "trace_id": trace_id,
        "request_id": request_id,
    }
