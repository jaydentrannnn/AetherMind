"""In-process job runtime and SSE fan-out for research execution."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app import db
from app.config import settings
from app.memory import sqlite_store
from app.models import ResearchJob
from app.schemas import Claim, Citation, Report, Section, Source


def _format_sse(payload: str) -> str:
    """Wrap one SSE data payload line with the protocol delimiter."""
    return f"data: {payload}\n\n"


def _event_type(node_name: str) -> str:
    """Map LangGraph node names to frontend SSE event categories."""
    mapping = {
        "planner": "planner",
        "researcher": "researcher",
        "synthesizer": "synthesizer",
        "guardrails": "guardrails",
        "critic": "critic",
        "memory_writer": "memory",
    }
    return mapping.get(node_name, "tool" if "tool" in node_name else "researcher")


@dataclass
class JobRuntime:
    """Track queue, replay buffer, and execution task for one job id."""

    queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    replay: deque[str] = field(default_factory=lambda: deque(maxlen=200))
    task: asyncio.Task[None] | None = None


class JobManager:
    """Launch graph jobs and publish stream events to SSE subscribers."""

    def __init__(self) -> None:
        """Initialize in-memory runtime maps for active and completed jobs."""
        self._jobs: dict[str, JobRuntime] = {}
        self._lock = asyncio.Lock()

    async def start(self, topic: str, options: dict[str, Any] | None, user_id: str | None) -> str:
        """Create one ResearchJob row and schedule async execution."""
        del options
        job_id = str(uuid.uuid4())
        resolved_user_id = user_id or sqlite_store.ensure_default_user()
        with db.SessionLocal() as session:
            session.add(
                ResearchJob(
                    id=job_id,
                    user_id=resolved_user_id,
                    topic=topic,
                    status="pending",
                )
            )
            session.commit()

        async with self._lock:
            runtime = self._jobs.setdefault(job_id, JobRuntime())
            runtime.task = asyncio.create_task(self._run(job_id=job_id, topic=topic))
        return job_id

    async def subscribe(self, job_id: str) -> AsyncIterator[str]:
        """Yield SSE lines for a job, replaying buffered events first."""
        runtime = self._jobs.setdefault(job_id, JobRuntime())
        for item in runtime.replay:
            yield item
        while True:
            item = await runtime.queue.get()
            yield item
            if item == _format_sse("[DONE]"):
                return

    async def _emit(self, job_id: str, payload: dict[str, Any] | str) -> None:
        """Publish one payload to queue and replay buffer for subscribers."""
        runtime = self._jobs.setdefault(job_id, JobRuntime())
        serialized = payload if isinstance(payload, str) else json.dumps(payload)
        line = _format_sse(serialized)
        runtime.replay.append(line)
        await runtime.queue.put(line)

    def _supports_real_driver(self) -> bool:
        """Return whether required model settings are present for real execution."""
        return bool(settings.MODEL_PLANNER and settings.MODEL_SYNTH)

    async def _run(self, *, job_id: str, topic: str) -> None:
        """Execute one job via real graph driver or deterministic fallback."""
        try:
            if self._supports_real_driver():
                await self._run_real_driver(job_id=job_id, topic=topic)
            else:
                await self._run_fallback_driver(job_id=job_id, topic=topic)
        except Exception as exc:  # pragma: no cover - defensive path
            await self._emit(job_id, {"type": "error", "msg": str(exc)})
        finally:
            await self._emit(job_id, "[DONE]")
            with db.SessionLocal() as session:
                job = session.get(ResearchJob, job_id)
                if job is not None:
                    job.status = "completed"
                    session.commit()

    async def _run_real_driver(self, *, job_id: str, topic: str) -> None:
        """Stream events from LangGraph astream_events into frontend envelopes."""
        # Import lazily so environments without optional graph deps can still use fallback mode.
        from app.agent.graph import build_graph

        graph = build_graph(checkpointer=None)
        started = time.monotonic()
        initial_state = {
            "topic": topic,
            "job_id": job_id,
            "user_id": sqlite_store.ensure_default_user(),
        }
        async for event in graph.astream_events(
            initial_state,
            version="v2",
            config={"configurable": {"thread_id": job_id}},
        ):
            event_name = event.get("event", "")
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")
            if not node_name and "name" in event:
                node_name = str(event["name"])
            if not node_name:
                continue
            msg = event_name or f"{node_name} event"
            await self._emit(
                job_id,
                {
                    "type": _event_type(node_name),
                    "msg": msg,
                    "ts": int((time.monotonic() - started) * 1000),
                    "trace_id": job_id,
                },
            )

    async def _run_fallback_driver(self, *, job_id: str, topic: str) -> None:
        """Emit deterministic canned events and persist a synthetic report."""
        for event_type, message in [
            ("planner", "Planned sub-questions"),
            ("researcher", "Gathering evidence"),
            ("tool", "web_search complete"),
            ("synthesizer", "Draft generated"),
            ("guardrails", "All checks passed"),
            ("critic", "Approved"),
        ]:
            await self._emit(job_id, {"type": event_type, "msg": message, "trace_id": job_id})

        source = Source(
            id="src-1",
            source_type="web_search",
            title="Fallback Source",
            url_or_doi="https://example.com/fallback",
            snippet="Fallback snippet.",
        )
        draft = Report(
            title=f"Fallback report for {topic}",
            summary="Fallback generated for local test/dev execution.",
            markdown="## Findings\n\nDeterministic fallback output.",
            sections=[
                Section(
                    title="Findings",
                    content="Deterministic fallback output.",
                    claims=[
                        Claim(
                            text="Fallback claim",
                            confidence=0.8,
                            citations=[
                                Citation(
                                    source_id=source.id,
                                    snippet="Fallback snippet.",
                                    verified=True,
                                )
                            ],
                        )
                    ],
                )
            ],
        )
        sqlite_store.persist_report(
            job_id=job_id,
            user_id=sqlite_store.ensure_default_user(),
            topic=topic,
            report=draft,
            rubric_score=None,
            sources_map={source.id: source},
            metadata={
                "sources": [source.model_dump(mode="json")],
                "trace_id": job_id,
            },
        )


@lru_cache(maxsize=1)
def get_job_manager() -> JobManager:
    """Return a process-wide singleton job manager."""
    return JobManager()
