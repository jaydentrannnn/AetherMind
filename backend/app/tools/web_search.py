"""Tavily-backed web search tool."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.schemas import ToolResult
from app.tools.base import BaseTool


class ToolConfigError(RuntimeError):
    """Raised when required tool configuration is missing."""


class WebSearchTool(BaseTool):
    """Search the web via Tavily and return citable snippets."""

    name = "web_search"
    description = "Search the web and return concise evidence snippets."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
            },
            "search_depth": {
                "type": "string",
                "enum": ["basic", "advanced"],
                "default": "basic",
            },
        },
        "required": ["query"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute a Tavily search for the given query."""
        api_key = settings.TAVILY_API_KEY
        if not api_key:
            raise ToolConfigError("TAVILY_API_KEY is required for web_search.")
        query = str(kwargs["query"])
        max_results = int(kwargs.get("max_results", 5))
        search_depth = str(kwargs.get("search_depth", "basic")).lower()
        if search_depth not in {"basic", "advanced"}:
            search_depth = "basic"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth,
                },
            )
            response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

        _SNIPPET_CHARS = 600
        lines: list[str] = []
        for item in results:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            snippet = (item.get("content") or "").strip().replace("\n", " ")
            if len(snippet) > _SNIPPET_CHARS:
                snippet = snippet[:_SNIPPET_CHARS].rstrip() + "…"
            entry = f"- {title} ({url})"
            if snippet:
                entry += f"\n  {snippet}"
            lines.append(entry)
        content = "\n".join(lines) if lines else "No results returned."
        first = results[0] if results else {}
        source = self._source_registry.create(
            source_type="web_search",
            title=first.get("title") or f"Web search: {query}",
            url_or_doi=first.get("url"),
            snippet=first.get("content"),
            metadata={"query": query, "results": results},
        )
        return ToolResult(content=content, source=source)
