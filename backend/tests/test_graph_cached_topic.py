"""Integration test: second run on same topic populates planner memory context."""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db
from app.agent.graph import build_graph
from app.agent.nodes.planner import PlannerOutput
from app.db import Base
from app.memory.service import MemoryService
from app.schemas import (
    Critique,
    EntailmentVerdict,
    Finding,
    PreferenceDeltaList,
    Report,
    Source,
    SubQuestion,
)


class _FakeRouter:
    """Return deterministic structured responses; no real LLM calls."""

    async def structured(self, task, messages, schema, **kwargs):
        del messages, kwargs
        if schema is PlannerOutput:
            return PlannerOutput(
                sub_questions=[
                    SubQuestion(
                        id="sq-1",
                        question="What do we know?",
                        rationale="cover scope",
                        suggested_tools=["web_search"],
                    )
                ]
            )
        if schema is Report:
            return Report(
                title="Draft",
                summary="Summary text",
                markdown="Report body " * 60,
                sections=[],
            )
        if schema is Critique:
            return Critique(score=4.5, approved=True, directives=[])
        if schema is EntailmentVerdict:
            return EntailmentVerdict(entails=True, confidence=0.9)
        if schema is PreferenceDeltaList:
            return PreferenceDeltaList(deltas=[])
        raise AssertionError(f"unexpected schema {schema}")


class _FakeVectorStore:
    """In-memory stub; forces sqlite fallback in MemoryService.recall."""

    async def add_report_summary(self, *a, **kw):
        pass

    async def query_reports(self, *a, **kw):
        return []  # empty → sqlite_store.list_reports_for_topic fallback

    async def add_preference_text(self, *a, **kw):
        pass

    async def query_preferences(self, *a, **kw):
        return []


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Provide an isolated SQLite DB and patch db module globals."""
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", session_factory)
    Base.metadata.create_all(bind=engine)
    return engine


async def _run_graph(
    topic: str,
    *,
    memory_svc: MemoryService,
    monkeypatch,
    thread_id: str,
) -> dict:
    """Build a fresh compiled graph, stub the researcher, and invoke it."""

    async def _fake_researcher(state):
        return {
            "findings": [Finding(sub_question_id="sq-1", answer="ans", evidence=[], source_ids=[])],
            "sources": [Source(source_type="web_search", title="Source 1", url_or_doi=None)],
        }

    monkeypatch.setattr("app.agent.graph.researcher_node", _fake_researcher)
    monkeypatch.setattr("app.agent.nodes.planner.get_memory_service", lambda: memory_svc)
    monkeypatch.setattr("app.agent.nodes.memory_writer.get_memory_service", lambda: memory_svc)

    router = _FakeRouter()
    graph = build_graph(llm_router=router, checkpointer=InMemorySaver())
    return await graph.ainvoke(
        {"topic": topic, "job_id": f"job-{thread_id}", "user_id": "default"},
        config={"configurable": {"thread_id": thread_id}},
    )


@pytest.mark.asyncio
async def test_second_run_sees_past_report(isolated_db, monkeypatch):
    """Planner on second run should receive past_reports from memory recall."""
    topic = "quantum error correction"
    svc = MemoryService(llm_router=_FakeRouter(), vector_store=_FakeVectorStore())

    # First run
    r1 = await _run_graph(topic, memory_svc=svc, monkeypatch=monkeypatch, thread_id="run-1")
    assert r1["approved"] is True

    # Verify memory_writer actually persisted the report
    recall_after_first = await svc.recall(topic)
    assert recall_after_first["past_reports"], (
        "memory_writer must persist the report so the second run can recall it"
    )

    # Second run (fresh MemoryService to clear any in-memory state, still same DB)
    svc2 = MemoryService(llm_router=_FakeRouter(), vector_store=_FakeVectorStore())
    r2 = await _run_graph(topic, memory_svc=svc2, monkeypatch=monkeypatch, thread_id="run-2")
    assert r2["approved"] is True

    past_reports = r2.get("memory_context", {}).get("past_reports", [])
    assert past_reports, (
        "Planner on 2nd run must receive past_reports — "
        "memory recall should return the report from the first run"
    )


@pytest.mark.asyncio
async def test_unseen_topic_has_empty_memory_context(isolated_db, monkeypatch):
    """Baseline: a never-researched topic should produce an empty past_reports list."""
    topic = "completely unknown topic xyz-999"
    svc = MemoryService(llm_router=_FakeRouter(), vector_store=_FakeVectorStore())

    result = await _run_graph(topic, memory_svc=svc, monkeypatch=monkeypatch, thread_id="baseline-1")
    assert result["approved"] is True
    # First run has no prior history
    assert result.get("memory_context", {}).get("past_reports", []) == []
