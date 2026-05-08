"""In-process job runtime and SSE fan-out for research execution."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.agent.depth import DepthLevel, normalize_depth
from app import db
from app.config import settings
from app.memory import sqlite_store
from app.models import ResearchJob
from app.observability import get_tracer
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
    """Track per-subscriber queues, replay buffer, and execution task for one job id."""

    replay: deque[str] = field(default_factory=lambda: deque(maxlen=200))
    subscribers: set[asyncio.Queue[str]] = field(default_factory=set)
    task: asyncio.Task[None] | None = None
    completed_at: float | None = None


class JobManager:
    """Launch graph jobs and publish stream events to SSE subscribers."""

    def __init__(self) -> None:
        """Initialize in-memory runtime maps for active and completed jobs."""
        self._jobs: dict[str, JobRuntime] = {}
        self._lock = asyncio.Lock()
        self._replay_ttl_s = 60.0
        self._subscriber_queue_max = 500

    async def start(self, topic: str, options: dict[str, Any] | None, user_id: str | None) -> str:
        """Create one ResearchJob row and schedule async execution."""
        job_id = str(uuid.uuid4())
        resolved_options = options or {}
        resolved_depth = normalize_depth(
            resolved_options.get("depth") if isinstance(resolved_options, dict) else None
        )
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
            runtime.task = asyncio.create_task(
                self._run(
                    job_id=job_id,
                    topic=topic,
                    depth=resolved_depth,
                    user_id=resolved_user_id,
                )
            )
        return job_id

    async def subscribe(self, job_id: str) -> AsyncIterator[str]:
        """Yield SSE lines for a job, replaying buffered events then live events."""
        runtime = self._jobs.get(job_id)
        if runtime is None:
            with db.SessionLocal() as session:
                job = session.get(ResearchJob, job_id)
            if job is None:
                raise KeyError(job_id)
            if job.status in {"completed", "failed"}:
                yield _format_sse("[DONE]")
                return
            yield _format_sse(json.dumps({"type": "error", "msg": "Job runtime unavailable"}))
            yield _format_sse("[DONE]")
            return
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=self._subscriber_queue_max)
        for item in runtime.replay:
            self._safe_queue_put(q, item)
        runtime.subscribers.add(q)
        try:
            while True:
                item = await q.get()
                yield item
                if item == _format_sse("[DONE]"):
                    return
        finally:
            runtime.subscribers.discard(q)

    @staticmethod
    def _safe_queue_put(q: asyncio.Queue[str], item: str) -> None:
        """Enqueue an SSE line without blocking, dropping oldest on overflow."""
        try:
            q.put_nowait(item)
            return
        except asyncio.QueueFull:
            pass
        try:
            _ = q.get_nowait()
        except asyncio.QueueEmpty:
            return
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            return

    async def _emit(self, job_id: str, payload: dict[str, Any] | str) -> None:
        """Publish one payload to all subscriber queues and the replay buffer."""
        runtime = self._jobs.setdefault(job_id, JobRuntime())
        line = _format_sse(payload if isinstance(payload, str) else json.dumps(payload))
        runtime.replay.append(line)
        for q in list(runtime.subscribers):
            self._safe_queue_put(q, line)

    def _supports_real_driver(self) -> bool:
        """Return whether required model settings are present for real execution."""
        return bool(settings.MODEL_PLANNER and settings.MODEL_SYNTH)

    async def _run(self, *, job_id: str, topic: str, depth: DepthLevel, user_id: str) -> None:
        """Execute one job via real graph driver or deterministic fallback."""
        tracer = get_tracer()
        trace_id = tracer.start_trace(job_id=job_id, topic=topic)
        failed = False
        try:
            if self._supports_real_driver():
                await self._run_real_driver(
                    job_id=job_id,
                    topic=topic,
                    depth=depth,
                    user_id=user_id,
                    trace_id=trace_id,
                )
            else:
                await self._run_fallback_driver(
                    job_id=job_id,
                    topic=topic,
                    depth=depth,
                    user_id=user_id,
                    trace_id=trace_id,
                )
        except Exception as exc:  # pragma: no cover - defensive path
            failed = True
            tracer.end_trace(trace_id, error=str(exc))
            await self._emit(job_id, {"type": "error", "msg": str(exc)})
        finally:
            if not failed:
                tracer.end_trace(trace_id, output={"status": "completed"})
            await self._emit(job_id, "[DONE]")
            async with self._lock:
                runtime = self._jobs.get(job_id)
                if runtime is not None:
                    runtime.completed_at = time.monotonic()
                    asyncio.create_task(self._cleanup_after_ttl(job_id))
            with db.SessionLocal() as session:
                job = session.get(ResearchJob, job_id)
                if job is not None:
                    job.status = "failed" if failed else "completed"
                    session.commit()

    async def _cleanup_after_ttl(self, job_id: str) -> None:
        """Evict completed jobs after a short replay TTL to prevent leaks."""
        await asyncio.sleep(self._replay_ttl_s)
        async with self._lock:
            runtime = self._jobs.get(job_id)
            if runtime is None:
                return
            if runtime.subscribers:
                return
            if runtime.task is not None and not runtime.task.done():
                return
            self._jobs.pop(job_id, None)

    async def _run_real_driver(
        self,
        *,
        job_id: str,
        topic: str,
        depth: DepthLevel,
        user_id: str,
        trace_id: str | None = None,
    ) -> None:
        """Stream events from LangGraph astream_events into frontend envelopes."""
        # Import lazily so environments without optional graph deps can still use fallback mode.
        from app.agent.graph import build_graph, open_checkpointer

        async with open_checkpointer() as checkpointer:
            graph = build_graph(checkpointer=checkpointer)
            started = time.monotonic()
            initial_state = {
                "topic": topic,
                "job_id": job_id,
                "user_id": user_id,
                "depth": depth,
                "trace_id": trace_id,
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
                        "trace_id": trace_id,
                    },
                )

    async def _run_fallback_driver(
        self,
        *,
        job_id: str,
        topic: str,
        depth: DepthLevel,
        user_id: str,
        trace_id: str | None = None,
    ) -> None:
        """Emit deterministic canned events and persist a synthetic report."""
        for event_type, message in [
            ("planner", "Planned sub-questions"),
            ("researcher", "Gathering evidence"),
            ("tool", "web_search complete"),
            ("synthesizer", "Draft generated"),
            ("guardrails", "All checks passed"),
            ("critic", "Approved"),
        ]:
            await self._emit(job_id, {"type": event_type, "msg": message, "trace_id": trace_id or job_id})

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
            user_id=user_id,
            topic=topic,
            report=draft,
            rubric_score=None,
            sources_map={source.id: source},
            metadata={
                "sources": [source.model_dump(mode="json")],
                "trace_id": trace_id or job_id,
                "depth": depth,
            },
        )


@lru_cache(maxsize=1)
def get_job_manager() -> JobManager:
    """Return a process-wide singleton job manager."""
    return JobManager()
