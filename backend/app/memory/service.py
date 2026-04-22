"""Hybrid memory service combining SQLite and Chroma recall/write behavior."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.llm.router import Router, router as default_router
from app.memory import sqlite_store
from app.memory.vector_store import VectorStore
from app.schemas import PreferenceDeltaList, RecalledMemory, Report, Source


class MemoryService:
    """Orchestrate structured SQL memory and semantic vector memory."""

    def __init__(
        self,
        *,
        llm_router: Router | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        """Initialize router and vector dependencies for read/write flows."""
        self._router = llm_router or default_router
        self._vector_store = vector_store or VectorStore()

    async def recall(self, topic: str, *, user_id: str | None = None) -> dict[str, Any]:
        """Return planner-ready memory context with stable keys and defaults."""
        resolved_user_id = user_id or sqlite_store.ensure_default_user()
        preferences = sqlite_store.get_preferences(resolved_user_id)
        allow_domains, deny_domains = sqlite_store.get_domain_lists(resolved_user_id)
        semantic_preferences = await self._vector_store.query_preferences(topic, resolved_user_id, k=5)
        past_reports = await self._vector_store.query_reports(topic, k=5)
        if not past_reports:
            past_reports = sqlite_store.list_reports_for_topic(topic, limit=5)
        recalled = RecalledMemory(
            preferences=preferences,
            allow_domains=allow_domains,
            deny_domains=deny_domains,
            past_reports=past_reports,
            semantic_preferences=semantic_preferences,
        )
        return recalled.model_dump()

    async def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist report tree and feedback-derived preference deltas."""
        draft = payload.get("draft")
        if not isinstance(draft, Report):
            return {"report_id": None, "claims_persisted": 0, "prefs_extracted": 0}

        user_id = payload.get("user_id") or sqlite_store.ensure_default_user()
        topic = str(payload.get("topic") or draft.title)
        sources = payload.get("sources") or []
        sources_map = {source.id: source for source in sources if isinstance(source, Source)}
        critique = payload.get("critique")
        rubric_score = getattr(critique, "score", None)
        report_id = sqlite_store.persist_report(
            job_id=payload.get("job_id"),
            user_id=user_id,
            topic=topic,
            report=draft,
            rubric_score=rubric_score,
            sources_map=sources_map,
        )

        summary_text = draft.summary or draft.title
        await self._vector_store.add_report_summary(report_id=report_id, topic=topic, summary=summary_text)

        feedback = payload.get("feedback")
        deltas = PreferenceDeltaList(deltas=[])
        if feedback:
            feedback_text = str(feedback)
            deltas = await self._router.structured(
                "pref_extract",
                [
                    {
                        "role": "user",
                        "content": (
                            "Extract stable user preferences from the feedback text and "
                            "return deltas.\nFeedback:\n"
                            f"{feedback_text}"
                        ),
                    }
                ],
                PreferenceDeltaList,
            )

        for delta in deltas.deltas:
            sqlite_store.upsert_preference(user_id, delta.key, delta.value)
            await self._vector_store.add_preference_text(user_id, delta.key, f"{delta.key}: {delta.value}")

        claims_persisted = sum(len(section.claims) for section in draft.sections)
        return {
            "report_id": report_id,
            "claims_persisted": claims_persisted,
            "prefs_extracted": len(deltas.deltas),
        }


@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    """Return a process-wide singleton memory service instance."""
    return MemoryService()
# memory.recall / memory.write — memory_service (plan §6).
