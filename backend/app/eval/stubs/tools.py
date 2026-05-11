"""Stub tools and tool-catalog patcher for the researcher stage eval.

The researcher node calls :func:`app.agent.nodes.researcher._build_tool_catalog`
to instantiate real tools. For per-node eval we want no network access and
fully deterministic outputs, so the context manager below temporarily replaces
that catalog factory with one that returns ``StubTool`` instances backed by
fixture-defined payloads.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from pydantic import BaseModel, Field

from app.schemas import Source, SourceType, ToolResult
from app.tools.base import BaseTool, SourceRegistry


class StubSourceSpec(BaseModel):
    """JSON-fixture-friendly spec used to register a stub Source."""

    source_type: SourceType
    title: str | None = None
    url_or_doi: str | None = None
    snippet: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StubToolSpec(BaseModel):
    """JSON-fixture-friendly spec describing one canned tool result."""

    content: str
    source: StubSourceSpec


class StubTool(BaseTool):
    """Tool that returns a canned ToolResult without any network access."""

    description = "Stubbed tool used by the per-node eval harness."
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }

    def __init__(
        self,
        *,
        source_registry: SourceRegistry,
        tool_name: str,
        spec: StubToolSpec,
    ) -> None:
        """Initialize the stub with a per-tool canned payload."""
        super().__init__(source_registry=source_registry)
        # `name` is set on the instance rather than the class so multiple stubs
        # with different identities can coexist in the same catalog.
        self.name = tool_name
        self._spec = spec

    async def run(self, **kwargs: Any) -> ToolResult:
        """Register a fresh Source and return the canned ToolResult."""
        del kwargs
        source = self._source_registry.register(
            Source(
                source_type=self._spec.source.source_type,
                title=self._spec.source.title,
                url_or_doi=self._spec.source.url_or_doi,
                snippet=self._spec.source.snippet,
                metadata=self._spec.source.metadata,
            )
        )
        return ToolResult(content=self._spec.content, source=source)


@contextmanager
def stub_tool_catalog(catalog_spec: dict[str, StubToolSpec]) -> Iterator[None]:
    """Temporarily swap the researcher tool catalog for stub-backed tools.

    Args:
        catalog_spec: Mapping of tool name (e.g. ``"web_search"``) to the canned
            payload that tool should return for any invocation.

    The patch targets ``app.agent.nodes.researcher._build_tool_catalog`` so the
    swap is invisible to the rest of the agent graph. Tools requested by a
    sub-question but not present in ``catalog_spec`` simply do not appear in
    the catalog, mirroring real-world "tool unavailable" behavior.
    """
    from app.agent.nodes import researcher as researcher_module

    original = researcher_module._build_tool_catalog

    def _patched(source_registry: SourceRegistry) -> dict[str, BaseTool]:
        """Return stub tools for every catalog_spec entry."""
        return {
            tool_name: StubTool(
                source_registry=source_registry,
                tool_name=tool_name,
                spec=spec,
            )
            for tool_name, spec in catalog_spec.items()
        }

    researcher_module._build_tool_catalog = _patched
    try:
        yield
    finally:
        researcher_module._build_tool_catalog = original
