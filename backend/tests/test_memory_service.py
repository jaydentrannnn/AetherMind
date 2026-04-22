"""Tests for the Phase 6 hybrid memory service behavior."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db
from app.db import Base
from app.memory import sqlite_store
from app.memory.service import MemoryService, get_memory_service
from app.schemas import (
    Citation,
    Claim,
    Critique,
    PreferenceDelta,
    PreferenceDeltaList,
    Report,
    Section,
    Source,
)


class FakeVectorStore:
    """In-memory vector store test double for deterministic assertions."""

    def __init__(self) -> None:
        """Initialize in-memory collections for report and preference vectors."""
        self.report_rows: list[dict] = []
        self.preference_rows: list[dict] = []

    async def add_report_summary(self, report_id: str, topic: str, summary: str) -> None:
        """Store one report summary row."""
        self.report_rows.append({"report_id": report_id, "topic": topic, "summary": summary, "score": 1.0})

    async def query_reports(self, topic: str, k: int = 5) -> list[dict]:
        """Return matching report rows by topic substring."""
        del k
        return [row for row in self.report_rows if topic.lower() in row["topic"].lower()]

    async def add_preference_text(self, user_id: str, key: str, text: str) -> None:
        """Store one semantic preference row."""
        self.preference_rows.append({"user_id": user_id, "key": key, "text": text, "score": 1.0})

    async def query_preferences(self, topic: str, user_id: str, k: int = 5) -> list[dict]:
        """Return preference rows for one user."""
        del topic, k
        return [row for row in self.preference_rows if row["user_id"] == user_id]


class FakeRouter:
    """Return deterministic preference deltas for memory.write tests."""

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Return one preference delta for pref_extract calls."""
        del messages, schema, kwargs
        if task != "pref_extract":
            raise AssertionError(f"unexpected task: {task}")
        return PreferenceDeltaList(deltas=[PreferenceDelta(key="tone", value="concise", rationale="user request")])


@pytest.fixture()
def in_memory_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bind SessionLocal to an isolated in-memory SQLite database."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(db, "SessionLocal", testing_session)
    Base.metadata.create_all(bind=engine)
    get_memory_service.cache_clear()
    yield
    get_memory_service.cache_clear()


def _sample_report(source_id: str) -> Report:
    """Build one report with a single claim/citation pair."""
    return Report(
        title="Persisted report",
        summary="Short summary",
        markdown="Report body",
        sections=[
            Section(
                title="Main",
                content="Main content",
                claims=[
                    Claim(
                        text="Claim text",
                        confidence=0.8,
                        citations=[Citation(source_id=source_id, snippet="Evidence snippet", verified=True)],
                    )
                ],
            )
        ],
    )


async def test_recall_empty_returns_full_shape(in_memory_db: None) -> None:
    """Recall should always return all expected keys with empty defaults."""
    service = MemoryService(llm_router=FakeRouter(), vector_store=FakeVectorStore())
    recalled = await service.recall("phase six")
    assert recalled == {
        "preferences": {},
        "allow_domains": [],
        "deny_domains": [],
        "past_reports": [],
        "semantic_preferences": [],
    }


async def test_recall_with_prefs_and_domain_lists(in_memory_db: None) -> None:
    """Recall should include persisted preferences and allow/deny lists."""
    user_id = sqlite_store.ensure_default_user()
    sqlite_store.upsert_preference(user_id, "style", "executive")
    sqlite_store.upsert_preference(user_id, "allow_domains", json.dumps(["example.com"]))
    sqlite_store.upsert_preference(user_id, "deny_domains", json.dumps(["blocked.com"]))
    service = MemoryService(llm_router=FakeRouter(), vector_store=FakeVectorStore())
    recalled = await service.recall("topic", user_id=user_id)
    assert recalled["preferences"]["style"] == "executive"
    assert recalled["allow_domains"] == ["example.com"]
    assert recalled["deny_domains"] == ["blocked.com"]


async def test_write_persists_report_claims_and_citations(in_memory_db: None) -> None:
    """write should persist the full report->claim->citation tree in SQL."""
    source = Source(source_type="web_search", title="Source", url_or_doi="https://example.com", snippet="Snippet")
    service = MemoryService(llm_router=FakeRouter(), vector_store=FakeVectorStore())
    result = await service.write(
        {
            "topic": "phase six",
            "draft": _sample_report(source.id),
            "sources": [source],
            "critique": Critique(score=4.5, approved=True, directives=[]),
        }
    )
    assert result["report_id"] is not None
    assert result["claims_persisted"] == 1


async def test_write_extracts_prefs_into_sql_and_vector_store(in_memory_db: None) -> None:
    """Feedback should trigger pref_extract and persist delta in SQL/vector layers."""
    source = Source(source_type="web_search", title="Source", url_or_doi="https://example.com", snippet="Snippet")
    vector_store = FakeVectorStore()
    service = MemoryService(llm_router=FakeRouter(), vector_store=vector_store)
    result = await service.write(
        {
            "topic": "phase six",
            "draft": _sample_report(source.id),
            "sources": [source],
            "feedback": "Please keep responses concise.",
        }
    )
    user_id = sqlite_store.ensure_default_user()
    prefs = sqlite_store.get_preferences(user_id)
    assert result["prefs_extracted"] == 1
    assert prefs["tone"] == "concise"
    assert len(vector_store.preference_rows) == 1


async def test_allow_deny_round_trip_via_preferences(in_memory_db: None) -> None:
    """Allow/deny preference JSON should round-trip through helper accessors."""
    user_id = sqlite_store.ensure_default_user()
    sqlite_store.upsert_preference(user_id, "allow_domains", json.dumps(["a.com", "b.com"]))
    sqlite_store.upsert_preference(user_id, "deny_domains", json.dumps(["x.com"]))
    allow, deny = sqlite_store.get_domain_lists(user_id)
    assert allow == ["a.com", "b.com"]
    assert deny == ["x.com"]


def test_ensure_default_user_is_idempotent(in_memory_db: None) -> None:
    """Default user creation should return the same id across calls."""
    first = sqlite_store.ensure_default_user()
    second = sqlite_store.ensure_default_user()
    assert first == second
