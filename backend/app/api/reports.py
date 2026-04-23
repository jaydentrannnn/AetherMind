"""Report retrieval and version metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app import db
from app.api import transforms
from app.memory import sqlite_store
from app.models import Report as ReportEntity
from app.models import ResearchJob
from app.schemas import GuardrailReport, Rubric, Source

router = APIRouter(tags=["reports"])


def _resolve_report(session: Session, report_id: str) -> ReportEntity | None:
    """Resolve a report identifier as row id first, then latest by job id."""
    by_id = session.scalar(select(ReportEntity).where(ReportEntity.id == report_id))
    if by_id is not None:
        return by_id
    return session.scalar(
        select(ReportEntity)
        .where(ReportEntity.job_id == report_id)
        .order_by(ReportEntity.version.desc())
    )


def _json_source_list(payload: dict) -> list[Source]:
    """Decode persisted source dictionaries into Source models."""
    out: list[Source] = []
    for item in payload.get("sources", []) or []:
        try:
            out.append(Source.model_validate(item))
        except Exception:
            continue
    return out


def _verified_ids_from_blob(payload: dict) -> set[str]:
    """Extract verified source ids from persisted report claim citations."""
    verified: set[str] = set()
    for section in payload.get("sections", []) or []:
        for claim in section.get("claims", []) or []:
            for citation in claim.get("citations", []) or []:
                if citation.get("verified") and citation.get("source_id"):
                    verified.add(str(citation["source_id"]))
    return verified


@router.get("/reports")
def list_reports(limit: int = 50) -> list[dict]:
    """List recent research jobs for the default user, with latest report id when present."""
    cap = min(max(limit, 1), 100)
    user_id = sqlite_store.ensure_default_user()
    latest_subq = (
        select(
            ReportEntity.job_id.label("job_id"),
            func.max(ReportEntity.version).label("max_v"),
        )
        .group_by(ReportEntity.job_id)
        .subquery()
    )
    with db.SessionLocal() as session:
        stmt = (
            select(ResearchJob, ReportEntity.id)
            .where(ResearchJob.user_id == user_id)
            .outerjoin(latest_subq, latest_subq.c.job_id == ResearchJob.id)
            .outerjoin(
                ReportEntity,
                and_(
                    ReportEntity.job_id == ResearchJob.id,
                    ReportEntity.version == latest_subq.c.max_v,
                ),
            )
            .order_by(ResearchJob.created_at.desc())
            .limit(cap)
        )
        rows = session.execute(stmt).all()
        return [
            transforms.research_job_summary_to_ui(job=row[0], latest_report_id=row[1])
            for row in rows
        ]


@router.get("/reports/{report_id}")
def get_report(report_id: str, request: Request) -> dict:
    """Return one report payload transformed to the frontend contract."""
    with db.SessionLocal() as session:
        report_row = _resolve_report(session, report_id)
        if report_row is None:
            raise HTTPException(status_code=404, detail="Report not found")
        payload = report_row.json_blob or {}
        sources = _json_source_list(payload)
        guardrails = (
            GuardrailReport.model_validate(payload["guardrail_report"])
            if payload.get("guardrail_report")
            else None
        )
        rubric = Rubric.model_validate(payload["rubric"]) if payload.get("rubric") else None
        return transforms.report_to_response(
            report_row=report_row,
            sources=sources,
            guardrails=guardrails,
            rubric=rubric,
            trace_id=payload.get("trace_id"),
            request_id=getattr(request.state, "request_id", None),
            depth=payload.get("depth", "standard"),
            verified_source_ids=_verified_ids_from_blob(payload),
        )


@router.get("/reports/{report_id}/versions")
def get_report_versions(report_id: str) -> list[dict]:
    """List version metadata rows for all reports in the same job."""
    with db.SessionLocal() as session:
        report_row = _resolve_report(session, report_id)
        if report_row is None:
            raise HTTPException(status_code=404, detail="Report not found")
        rows = session.scalars(
            select(ReportEntity)
            .where(ReportEntity.job_id == report_row.job_id)
            .order_by(ReportEntity.version.desc())
        ).all()
        return [transforms.version_to_ui(row) for row in rows]
