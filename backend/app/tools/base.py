"""Base contracts for tools and source registration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas import Source, SourceType, ToolResult


class SourceRegistry:
    """Registry for citable sources emitted by tool calls."""

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}

    def register(self, source: Source) -> Source:
        """Store a source by UUID and return the stored object."""
        self._sources[source.id] = source
        return source

    def create(
        self,
        *,
        source_type: SourceType,
        title: str | None,
        url_or_doi: str | None,
        snippet: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> Source:
        """Construct and register a source entry in one call."""
        source = Source(
            source_type=source_type,
            title=title,
            url_or_doi=url_or_doi,
            snippet=snippet,
            metadata=metadata or {},
        )
        return self.register(source)

    def get(self, source_id: str) -> Source | None:
        """Return a source by id when present."""
        return self._sources.get(source_id)

    def all(self) -> list[Source]:
        """Return every registered source."""
        return list(self._sources.values())


class BaseTool(ABC):
    """Base interface shared by all researcher tools."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def __init__(self, *, source_registry: SourceRegistry) -> None:
        self._source_registry = source_registry

    def function_schema(self) -> dict[str, Any]:
        """Return the JSON schema used for function-calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool and return citable output."""
