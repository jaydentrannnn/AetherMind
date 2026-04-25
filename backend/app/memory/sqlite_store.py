"""Synchronous SQLite repository helpers for memory persistence."""

from __future__ import annotations

import json

from sqlalchemy import func, select

from app import db
from app.config import settings
from app.models import Citation as CitationEntity
from app.models import Claim as ClaimEntity
from app.models import Preference as PreferenceEntity
from app.models import Report as ReportEntity
from app.models import ResearchJob
from app.models import User
from app.schemas import Report, Source

_MIN_MARKDOWN_CHARS = 200


def _derive_markdown_from_sections(report: Report) -> str:
    """Build a markdown document from structured sections as a fallback."""
    parts: list[str] = []
    if report.title:
        parts.append(f"# {report.title}")
    if report.summary:
        parts.append(report.summary.strip())
    for section in report.sections:
        title = (section.title or "").strip()
        body = (section.content or "").strip()
        if not title and not body:
            continue
        if title:
            parts.append(f"## {title}")
        if body:
            parts.append(body)
    return "\n\n".join(parts).strip()


def _normalized_markdown(report: Report) -> str:
    """Return report markdown, deriving from sections when blank or too sparse."""
    markdown = (report.markdown or "").strip()
    if len(markdown) >= _MIN_MARKDOWN_CHARS:
        return markdown
    derived = _derive_markdown_from_sections(report)
    if len(derived) > len(markdown):
        return derived
    return markdown


def ensure_default_user() -> str:
    """Return the default user id, creating the row on first use."""
    with db.SessionLocal() as session:
        existing = session.scalar(select(User).where(User.name == settings.DEFAULT_USER_NAME))
        if existing is not None:
            return existing.id
        user = User(name=settings.DEFAULT_USER_NAME)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def get_preferences(user_id: str) -> dict[str, str]:
    """Fetch all preference key/value pairs for one user."""
    with db.SessionLocal() as session:
        rows = session.scalars(select(PreferenceEntity).where(PreferenceEntity.user_id == user_id)).all()
        return {row.key: row.value for row in rows}


def get_domain_lists(user_id: str) -> tuple[list[str], list[str]]:
    """Return allow and deny domain lists decoded from preference JSON values."""
    prefs = get_preferences(user_id)

    def _parse_domains(raw: str | None) -> list[str]:
        """Decode a JSON list preference into a normalized string list."""
        if not raw:
            return []
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(decoded, list):
            return []
        return [str(item).strip() for item in decoded if str(item).strip()]

    return _parse_domains(prefs.get("allow_domains")), _parse_domains(prefs.get("deny_domains"))


def upsert_preference(user_id: str, key: str, value: str) -> None:
    """Insert or update one user preference under the unique (user,key) constraint."""
    with db.SessionLocal() as session:
        pref = session.scalar(
            select(PreferenceEntity).where(
                PreferenceEntity.user_id == user_id,
                PreferenceEntity.key == key,
            )
        )
        if pref is None:
            pref = PreferenceEntity(user_id=user_id, key=key, value=value)
            session.add(pref)
        else:
            pref.value = value
        session.commit()


def _resolve_or_create_job(*, job_id: str | None, user_id: str, topic: str) -> str:
    """Resolve an existing job id or create a new report container job."""
    with db.SessionLocal() as session:
        if job_id:
            existing = session.scalar(select(ResearchJob).where(ResearchJob.id == job_id))
            if existing is not None:
                return existing.id
        job = ResearchJob(id=job_id, user_id=user_id, topic=topic, status="completed")
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def persist_report(
    *,
    job_id: str | None,
    user_id: str,
    topic: str,
    report: Report,
    rubric_score: float | None,
    sources_map: dict[str, Source],
    metadata: dict | None = None,
) -> str:
    """Persist report/claim/citation rows and return the persisted report id."""
    resolved_job_id = _resolve_or_create_job(job_id=job_id, user_id=user_id, topic=topic)
    with db.SessionLocal() as session:
        max_version = session.scalar(
            select(func.max(ReportEntity.version)).where(ReportEntity.job_id == resolved_job_id)
        )
        normalized_markdown = _normalized_markdown(report)
        json_blob = report.model_dump(mode="json")
        json_blob["markdown"] = normalized_markdown
        if metadata:
            json_blob.update(metadata)
        report_row = ReportEntity(
            job_id=resolved_job_id,
            version=(max_version or 0) + 1,
            markdown=normalized_markdown,
            json_blob=json_blob,
            rubric_score=rubric_score,
        )
        session.add(report_row)
        session.flush()

        for section in report.sections:
            for claim in section.claims:
                claim_row = ClaimEntity(
                    report_id=report_row.id,
                    text=claim.text,
                    confidence=claim.confidence,
                )
                session.add(claim_row)
                session.flush()
                for citation in claim.citations:
                    mapped_source = sources_map.get(citation.source_id)
                    session.add(
                        CitationEntity(
                            claim_id=claim_row.id,
                            source_type=mapped_source.source_type if mapped_source else "url",
                            url_or_doi=mapped_source.url_or_doi if mapped_source else None,
                            title=mapped_source.title if mapped_source else None,
                            snippet=citation.snippet or (mapped_source.snippet if mapped_source else None),
                            verified_bool=citation.verified,
                        )
                    )

        session.commit()
        return report_row.id


def list_reports_for_topic(topic: str, limit: int = 5) -> list[dict]:
    """Return recent persisted reports for a topic when vector recall is empty."""
    with db.SessionLocal() as session:
        rows = session.scalars(
            select(ReportEntity)
            .join(ResearchJob, ReportEntity.job_id == ResearchJob.id)
            .where(ResearchJob.topic.ilike(f"%{topic}%"))
            .order_by(ReportEntity.created_at.desc())
            .limit(limit)
        ).all()
        out: list[dict] = []
        for row in rows:
            blob = row.json_blob or {}
            out.append(
                {
                    "report_id": row.id,
                    "title": blob.get("title"),
                    "summary": blob.get("summary"),
                    "score": row.rubric_score,
                }
            )
        return out
# Structured prefs / jobs / reports — memory_service (plan §6).
