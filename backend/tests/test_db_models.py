"""ORM persistence tests for Phase 3 SQLAlchemy models."""

from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Citation, Claim, Report, ResearchJob, User


def test_job_report_claim_citation_chain_persists() -> None:
    """Persist and reload the core report evidence relationship chain."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(name="Jayden")
        job = ResearchJob(user=user, topic="Phase 3 validation", status="complete")
        report = Report(job=job, version=1, markdown="report text")
        claim = Claim(report=report, text="A claim", confidence=0.8)
        citation = Citation(claim=claim, source_type="web", title="Source", verified_bool=True)

        session.add(citation)
        session.commit()
        session.expire_all()

        loaded_report = session.scalar(select(Report).where(Report.id == report.id))
        assert loaded_report is not None
        assert loaded_report.job.topic == "Phase 3 validation"
        assert len(loaded_report.claims) == 1
        assert loaded_report.claims[0].citations[0].title == "Source"
