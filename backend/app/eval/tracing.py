"""Optional Langfuse tracing utilities for eval harness runs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.config import settings


class EvalTracer:
    """No-op compatible tracer interface used by the eval harness."""

    def __init__(self) -> None:
        """Initialize no-op tracer state."""
        self._run_id: str | None = None

    def start_run(self, *, total_cases: int, deterministic_only: bool, fixtures_path: str) -> None:
        """Start a logical eval run trace."""
        del total_cases, deterministic_only, fixtures_path

    def start_case(self, *, case_id: str) -> dict[str, Any]:
        """Start a case-level trace span and return opaque span handle."""
        del case_id
        return {}

    def end_case(self, span: dict[str, Any], *, metrics: dict[str, float], judge_enabled: bool) -> None:
        """Finish a case-level trace span."""
        del span, metrics, judge_enabled

    def end_run(self, *, summary: dict[str, Any]) -> None:
        """Finalize the run trace and flush if needed."""
        del summary


class LangfuseEvalTracer(EvalTracer):
    """Langfuse-backed tracer with graceful no-op fallback semantics."""

    def __init__(self, *, client_factory: Callable[[], Any] | None = None) -> None:
        """Initialize Langfuse client lazily so dependency remains optional."""
        super().__init__()
        self._factory = client_factory
        self._client: Any | None = None

    def _get_client(self) -> Any | None:
        """Instantiate and memoize the Langfuse client if available/configured."""
        if self._client is not None:
            return self._client
        if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
            return None
        if self._factory is not None:
            self._client = self._factory()
            return self._client
        try:
            from langfuse import Langfuse  # type: ignore[import-not-found]
        except Exception:
            return None
        self._client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST or "https://cloud.langfuse.com",
        )
        return self._client

    def start_run(self, *, total_cases: int, deterministic_only: bool, fixtures_path: str) -> None:
        """Create a top-level Langfuse trace for the eval harness run."""
        client = self._get_client()
        if client is None:
            return
        trace = client.trace(
            name="eval_harness_run",
            metadata={
                "total_cases": total_cases,
                "deterministic_only": deterministic_only,
                "fixtures_path": fixtures_path,
            },
        )
        self._run_id = getattr(trace, "id", None)

    def start_case(self, *, case_id: str) -> dict[str, Any]:
        """Create a case-level span bound to the run trace."""
        client = self._get_client()
        if client is None or self._run_id is None:
            return {}
        span = client.span(trace_id=self._run_id, name="eval_case", metadata={"case_id": case_id})
        return {"span": span}

    def end_case(self, span: dict[str, Any], *, metrics: dict[str, float], judge_enabled: bool) -> None:
        """Annotate and end a case-level span."""
        raw_span = span.get("span")
        if raw_span is None:
            return
        raw_span.end(output={"metrics": metrics, "judge_enabled": judge_enabled})

    def end_run(self, *, summary: dict[str, Any]) -> None:
        """End run trace and flush Langfuse events."""
        client = self._get_client()
        if client is None:
            return
        if self._run_id is not None:
            client.trace(id=self._run_id, output=summary)
        client.flush()


def build_eval_tracer() -> EvalTracer:
    """Return a Langfuse tracer when possible, otherwise a no-op tracer."""
    return LangfuseEvalTracer()
