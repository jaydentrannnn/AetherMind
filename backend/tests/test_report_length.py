"""Tests covering report length/depth fixes: tools, critic, persistence."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.agent.nodes.critic import (
    SHALLOW_MARKDOWN_MIN_CHARS,
    SHALLOW_MIN_SECTIONS,
    critic_node,
)
from app.config import settings
from app.memory import sqlite_store
from app.schemas import Critique, Report, Section, Source
from app.tools import ArxivSearchTool, SourceRegistry, WebSearchTool


class _Router:
    """Minimal router stub capturing task tag and returning a critique."""

    def __init__(self, critique: Critique) -> None:
        """Store the critique to return for every structured call."""
        self.critique = critique
        self.last_task: str | None = None

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Record the task tag and return the preset critique."""
        del messages, schema, kwargs
        self.last_task = task
        return self.critique


async def test_web_search_content_includes_snippet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tavily snippets must appear in ToolResult.content, not only URLs."""
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")
    tool = WebSearchTool(source_registry=SourceRegistry())
    with respx.mock(assert_all_called=True) as mock:
        mock.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Result A",
                            "url": "https://example.com/a",
                            "content": "Detailed snippet A about the topic.",
                        },
                        {
                            "title": "Result B",
                            "url": "https://example.com/b",
                            "content": "Detailed snippet B with more context.",
                        },
                    ]
                },
            )
        )
        out = await tool.run(query="q", max_results=2)
    assert "Detailed snippet A about the topic." in out.content
    assert "Detailed snippet B with more context." in out.content
    assert "https://example.com/a" in out.content


async def test_arxiv_search_content_includes_abstract(monkeypatch: pytest.MonkeyPatch) -> None:
    """arXiv abstracts must be included in ToolResult.content per result."""
    tool = ArxivSearchTool(source_registry=SourceRegistry())

    def _fake(query: str, max_results: int) -> list[dict[str, str]]:
        """Return deterministic fake arXiv rows with summaries."""
        del query, max_results
        return [
            {
                "id": "http://arxiv.org/abs/1",
                "title": "Paper One",
                "summary": "Abstract one describing methodology.",
                "pdf_url": "",
            },
            {
                "id": "http://arxiv.org/abs/2",
                "title": "Paper Two",
                "summary": "Abstract two describing results.",
                "pdf_url": "",
            },
        ]

    monkeypatch.setattr(tool, "_search_sync", _fake)
    out = await tool.run(query="q", max_results=2)
    assert "Abstract one describing methodology." in out.content
    assert "Abstract two describing results." in out.content


async def test_critic_flags_shallow_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    """An approved-but-shallow draft must not finalize early."""
    monkeypatch.setattr(settings, "AGENT_MAX_REVISIONS", 3)
    router = _Router(Critique(score=4.5, approved=True, directives=[]))
    shallow = Report(title="t", markdown="short.", sections=[])
    result = await critic_node(
        {"topic": "x", "draft": shallow, "revisions": 0, "findings": []},
        llm_router=router,
    )
    assert result["approved"] is False
    assert result["next_action"] == "synthesizer"
    assert any("expand" in d.lower() for d in result["revision_directives"])


async def test_critic_approves_substantive_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    """A substantive approved draft should finalize to memory_writer."""
    monkeypatch.setattr(settings, "AGENT_MAX_REVISIONS", 3)
    router = _Router(Critique(score=4.7, approved=True, directives=[]))
    big_md = "x" * (SHALLOW_MARKDOWN_MIN_CHARS + 100)
    sections = [
        Section(title=f"S{i}", content="body " * 20) for i in range(SHALLOW_MIN_SECTIONS)
    ]
    draft = Report(title="t", markdown=big_md, sections=sections)
    result = await critic_node(
        {"topic": "x", "draft": draft, "revisions": 0, "findings": []},
        llm_router=router,
    )
    assert result["approved"] is True
    assert result["next_action"] == "memory_writer"


def test_persist_report_normalizes_blank_markdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """persist_report should derive markdown from sections when blank."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import db
    from app.db import Base
    from app.models import Report as ReportEntity

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'db.sqlite'}")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", testing_session)
    Base.metadata.create_all(bind=engine)

    user_id = sqlite_store.ensure_default_user()
    report = Report(
        title="Topic",
        summary="A short overview of the topic.",
        markdown="",
        sections=[
            Section(title="Intro", content="Paragraph of introduction text."),
            Section(title="Findings", content="Detailed findings paragraph."),
        ],
    )
    report_id = sqlite_store.persist_report(
        job_id=None,
        user_id=user_id,
        topic="Topic",
        report=report,
        rubric_score=None,
        sources_map={},
    )
    with db.SessionLocal() as session:
        row = session.get(ReportEntity, report_id)
        assert row is not None
        assert "Intro" in (row.markdown or "")
        assert "Paragraph of introduction text." in (row.markdown or "")
        assert "## Findings" in (row.markdown or "")


def test_persist_report_preserves_rich_markdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """persist_report should keep model-provided markdown when substantive."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import db
    from app.db import Base
    from app.models import Report as ReportEntity

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'db.sqlite'}")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", testing_session)
    Base.metadata.create_all(bind=engine)

    user_id = sqlite_store.ensure_default_user()
    rich = "# Title\n\n" + ("Paragraph with substantive analysis. " * 40)
    report = Report(title="Topic", markdown=rich, sections=[])
    report_id = sqlite_store.persist_report(
        job_id=None,
        user_id=user_id,
        topic="Topic",
        report=report,
        rubric_score=None,
        sources_map={},
    )
    with db.SessionLocal() as session:
        row = session.get(ReportEntity, report_id)
        assert row is not None
        assert row.markdown == rich.strip()
