"""Production Langfuse tracer for per-job agent tracing."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import settings


class AetherTracer:
    """No-op compatible tracer. All methods are safe to call when Langfuse is absent."""

    def start_trace(self, *, job_id: str, topic: str) -> str | None:
        """Create a top-level trace; return trace_id or None."""
        del job_id, topic
        return None

    def span(self, trace_id: str | None, *, name: str, input: Any = None) -> dict[str, Any]:
        """Open a span; return opaque span handle dict."""
        del trace_id, name, input
        return {}

    def end_span(self, span: dict[str, Any], *, output: Any = None, error: str | None = None) -> None:
        """Close span with output or error annotation."""
        del span, output, error

    def end_trace(self, trace_id: str | None, *, output: Any = None, error: str | None = None) -> None:
        """Finalize a trace."""
        del trace_id, output, error

    def flush(self) -> None:
        """Flush buffered events to Langfuse."""


class LangfuseAetherTracer(AetherTracer):
    """Langfuse-backed tracer with graceful no-op fallback."""

    def __init__(self) -> None:
        """Initialize with lazy client creation."""
        self._client: Any | None = None

    def _get_client(self) -> Any | None:
        """Instantiate and memoize the Langfuse client if available/configured.

        This repo treats Langfuse as optional. Some environments (or older SDK
        versions) may import successfully but not expose the methods we use. In
        that case, we silently disable tracing rather than crashing the job
        runtime (which would also break SSE streaming).
        """
        if self._client is not None:
            return self._client
        if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
            return None
        try:
            from langfuse import Langfuse  # type: ignore[import-not-found]
        except Exception:
            return None
        try:
            client = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST or "https://cloud.langfuse.com",
            )
        except Exception:
            return None
        if not hasattr(client, "trace") or not hasattr(client, "span"):
            return None
        self._client = client
        return self._client

    def start_trace(self, *, job_id: str, topic: str) -> str | None:
        """Create a top-level Langfuse trace for one research job."""
        client = self._get_client()
        if client is None:
            return None
        try:
            trace = client.trace(
                name="aethermind_job",
                input={"topic": topic},
                metadata={"job_id": job_id},
            )
        except Exception:
            return None
        return getattr(trace, "id", None)

    def span(self, trace_id: str | None, *, name: str, input: Any = None) -> dict[str, Any]:
        """Open a named span under the given trace."""
        client = self._get_client()
        if client is None or trace_id is None:
            return {}
        try:
            s = client.span(trace_id=trace_id, name=name, input=input)
        except Exception:
            return {}
        return {"span": s, "trace_id": trace_id}

    def end_span(self, span: dict[str, Any], *, output: Any = None, error: str | None = None) -> None:
        """Close a span with output or error metadata."""
        raw = span.get("span")
        if raw is None:
            return
        raw.end(
            output=output,
            level="ERROR" if error else "DEFAULT",
            status_message=error,
        )

    def end_trace(self, trace_id: str | None, *, output: Any = None, error: str | None = None) -> None:
        """Finalize a trace with output or error metadata."""
        client = self._get_client()
        if client is None or trace_id is None:
            return
        try:
            client.trace(
                id=trace_id,
                output=output,
                metadata={"error": error} if error else {},
            )
        except Exception:
            return

    def flush(self) -> None:
        """Flush all buffered Langfuse events."""
        client = self._get_client()
        if client is not None:
            client.flush()


@lru_cache(maxsize=1)
def get_tracer() -> AetherTracer:
    """Return the process-wide tracer singleton."""
    return LangfuseAetherTracer()
