"""SQLAlchemy ORM entities for the Phase 3 data model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    """Stores a user profile owning preferences and research jobs."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    preferences: Mapped[list[Preference]] = relationship(back_populates="user", cascade="all, delete-orphan")
    research_jobs: Mapped[list[ResearchJob]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Preference(Base):
    """Stores a key/value preference attached to one user."""

    __tablename__ = "preferences"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_preferences_user_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="preferences")


class ResearchJob(Base):
    """Tracks one end-to-end research request lifecycle."""

    __tablename__ = "research_jobs"
    __table_args__ = (Index("ix_research_jobs_user_created_at", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    rubric_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="research_jobs")
    reports: Mapped[list[Report]] = relationship(back_populates="job", cascade="all, delete-orphan")
    agent_traces: Mapped[list[AgentTrace]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Report(Base):
    """Stores one versioned report generated from a research job."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("job_id", "version", name="uq_reports_job_version"),
        Index("ix_reports_job_created_at", "job_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    json_blob: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rubric_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[ResearchJob] = relationship(back_populates="reports")
    claims: Mapped[list[Claim]] = relationship(back_populates="report", cascade="all, delete-orphan")
    feedback_items: Mapped[list[Feedback]] = relationship(back_populates="report", cascade="all, delete-orphan")


class Claim(Base):
    """Stores one extracted claim statement inside a report."""

    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    report: Mapped[Report] = relationship(back_populates="claims")
    citations: Mapped[list[Citation]] = relationship(back_populates="claim", cascade="all, delete-orphan")


class Citation(Base):
    """Stores one citation record linked to a claim."""

    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    url_or_doi: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_bool: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    claim: Mapped[Claim] = relationship(back_populates="citations")


class Feedback(Base):
    """Stores user feedback associated with a report output."""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_bool: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped[Report] = relationship(back_populates="feedback_items")


class AgentTrace(Base):
    """Captures execution metadata for each agent node event."""

    __tablename__ = "agent_traces"
    __table_args__ = (Index("ix_agent_traces_job_node", "job_id", "node"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node: Mapped[str] = mapped_column(String(128), nullable=False)
    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[ResearchJob] = relationship(back_populates="agent_traces")
