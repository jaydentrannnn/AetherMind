"""Memory-stage eval: in-memory SQLite + fake vector store recall/write."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db
from app.db import Base
from app.eval.models import StageCaseResult, StageReport
from app.eval.stages._common import build_stage_report, load_stage_fixtures
from app.memory import service as memory_service_module
from app.memory import sqlite_store
from app.memory.service import MemoryService
from app.schemas import (
    Citation,
    Claim,
    Critique,
    PreferenceDeltaList,
    Report,
    Section,
    Source,
)


class _FakeVectorStore:
    """In-memory vector store double for deterministic memory-stage assertions."""

    def __init__(self) -> None:
        """Initialize empty collections for report and preference vectors."""
        self.report_rows: list[dict[str, Any]] = []
        self.preference_rows: list[dict[str, Any]] = []

    async def add_report_summary(
        self, report_id: str, topic: str, summary: str, *, user_id: str
    ) -> None:
        """Append one report summary row."""
        del user_id
        self.report_rows.append({"report_id": report_id, "topic": topic, "summary": summary})

    async def query_reports(
        self, topic: str, *, user_id: str, k: int = 5
    ) -> list[dict[str, Any]]:
        """Return matching report rows filtered by topic substring."""
        del user_id, k
        return [row for row in self.report_rows if topic.lower() in row["topic"].lower()]

    async def add_preference_text(self, user_id: str, key: str, text: str) -> None:
        """Append one semantic preference row."""
        self.preference_rows.append({"user_id": user_id, "key": key, "text": text})

    async def query_preferences(
        self, topic: str, user_id: str, k: int = 5
    ) -> list[dict[str, Any]]:
        """Return preference rows for one user."""
        del topic, k
        return [row for row in self.preference_rows if row["user_id"] == user_id]


class _NoFeedbackRouter:
    """Router stub that asserts pref_extract is never called for the write tests."""

    async def structured(self, task, messages, schema, **kwargs):  # noqa: ANN001
        """Return an empty delta list; raises if any other task is invoked."""
        del messages, schema, kwargs
        if task != "pref_extract":
            raise AssertionError(f"unexpected memory-stage router task: {task!r}")
        return PreferenceDeltaList(deltas=[])


def _build_sample_report(source_id: str) -> Report:
    """Construct one realistic Report referencing the registered source."""
    return Report(
        title="Sample memory eval report",
        summary="Short summary for memory-stage eval.",
        markdown="Body referencing the sample source.",
        sections=[
            Section(
                title="Main",
                content="Main content.",
                claims=[
                    Claim(
                        text="Evidence-backed claim",
                        confidence=0.8,
                        citations=[Citation(source_id=source_id, snippet="Evidence snippet", verified=True)],
                    )
                ],
            )
        ],
    )


async def run_memory_stage(
    *,
    mock_llm: bool = True,
    deterministic_only: bool = True,
) -> StageReport:
    """Validate hybrid memory recall and write under isolated SQLite + fake Chroma.

    Args:
        mock_llm: Always True for this stage; the fake router refuses any non
            ``pref_extract`` call so test isolation is guaranteed.
        deterministic_only: Always True; no LLM judge is used.
    """
    del mock_llm
    cases = load_stage_fixtures("memory")
    results: list[StageCaseResult] = []

    # Save and replace the SQLAlchemy session factory so each case runs against
    # a private in-memory database. We restore after the whole stage finishes.
    original_session_local = db.SessionLocal
    original_engine = db.engine
    original_get_memory_service = memory_service_module.get_memory_service

    for case in cases:
        case_id = case["case_id"]
        try:
            engine = create_engine("sqlite+pysqlite:///:memory:")
            testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db.SessionLocal = testing_session  # type: ignore[assignment]
            Base.metadata.create_all(bind=engine)

            vector_store = _FakeVectorStore()
            service = MemoryService(llm_router=_NoFeedbackRouter(), vector_store=vector_store)
            memory_service_module.get_memory_service = lambda: service  # type: ignore[assignment]

            user_id = sqlite_store.ensure_default_user()
            for key, value in case.get("preferences", {}).items():
                sqlite_store.upsert_preference(user_id, key, value)
            if case.get("allow_domains"):
                sqlite_store.upsert_preference(
                    user_id, "allow_domains", json.dumps(case["allow_domains"])
                )
            if case.get("deny_domains"):
                sqlite_store.upsert_preference(
                    user_id, "deny_domains", json.dumps(case["deny_domains"])
                )

            recalled = await service.recall(case["topic"], user_id=user_id)
            # Allow/deny domains are persisted as JSON-encoded preference rows,
            # so they leak into recalled["preferences"]. We only require that
            # the explicit fixture preferences are a subset of recall output.
            recalled_prefs = recalled.get("preferences", {})
            prefs_subset_ok = all(
                recalled_prefs.get(key) == value
                for key, value in case.get("preferences", {}).items()
            )
            recall_ok = (
                prefs_subset_ok
                and recalled.get("allow_domains") == case.get("allow_domains", [])
                and recalled.get("deny_domains") == case.get("deny_domains", [])
            )

            source = Source(
                source_type="web_search",
                title="Sample",
                url_or_doi="https://example.org/sample",
                snippet="Evidence snippet",
            )
            first = await service.write(
                {
                    "topic": case["topic"],
                    "user_id": user_id,
                    "draft": _build_sample_report(source.id),
                    "sources": [source],
                    "critique": Critique(score=4.0, approved=True, directives=[]),
                }
            )
            second = await service.write(
                {
                    "topic": case["topic"],
                    "user_id": user_id,
                    "draft": _build_sample_report(source.id),
                    "sources": [source],
                    "critique": Critique(score=4.0, approved=True, directives=[]),
                }
            )

            diagnostics: list[str] = []
            if not recall_ok:
                diagnostics.append(f"recall mismatch: {recalled}")
            if first["report_id"] is None or second["report_id"] is None:
                diagnostics.append("write returned no report_id")
            if first["claims_persisted"] != 1 or second["claims_persisted"] != 1:
                diagnostics.append(
                    f"unexpected claims_persisted: first={first['claims_persisted']} second={second['claims_persisted']}"
                )

            deterministic: dict[str, Any] = {
                "recall_ok": recall_ok,
                "first_report_id_set": first["report_id"] is not None,
                "second_report_id_set": second["report_id"] is not None,
                "vector_rows_after_two_writes": len(vector_store.report_rows),
            }
            results.append(
                StageCaseResult(
                    case_id=case_id,
                    passed=(not diagnostics),
                    deterministic=deterministic,
                    diagnostics=diagnostics,
                )
            )
        except Exception as exc:
            results.append(
                StageCaseResult(
                    case_id=case_id,
                    passed=False,
                    deterministic={"error": True},
                    diagnostics=[f"memory stage raised: {exc!r}"],
                )
            )
        finally:
            memory_service_module.get_memory_service = original_get_memory_service  # type: ignore[assignment]
            db.SessionLocal = original_session_local  # type: ignore[assignment]
            db.engine = original_engine  # type: ignore[assignment]

    return build_stage_report(stage="memory", results=results, deterministic_only=True)
