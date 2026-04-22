"""arXiv search tool."""

from __future__ import annotations

import asyncio
from typing import Any

import arxiv

from app.schemas import ToolResult
from app.tools.base import BaseTool


class ArxivSearchTool(BaseTool):
    """Search arXiv and return paper metadata for citation."""

    name = "arxiv_search"
    description = "Search arXiv papers by query."
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
        },
        "required": ["query"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute an arXiv query and return formatted results."""
        query = str(kwargs["query"])
        max_results = int(kwargs.get("max_results", 5))
        results = await asyncio.to_thread(self._search_sync, query, max_results)

        lines = [f"- {item['title']} ({item['id']})" for item in results]
        content = "\n".join(lines) if lines else "No arXiv results returned."
        first = results[0] if results else {}
        source = self._source_registry.create(
            source_type="arxiv",
            title=first.get("title") or f"arXiv search: {query}",
            url_or_doi=first.get("pdf_url") or first.get("id"),
            snippet=first.get("summary"),
            metadata={"query": query, "results": results},
        )
        return ToolResult(content=content, source=source)

    def _search_sync(self, query: str, max_results: int) -> list[dict[str, str]]:
        """Run the arXiv client in a thread-friendly synchronous function."""
        search = arxiv.Search(
            query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
        )
        client = arxiv.Client()
        out: list[dict[str, str]] = []
        for result in client.results(search):
            out.append(
                {
                    "id": result.entry_id,
                    "title": result.title,
                    "summary": result.summary,
                    "pdf_url": result.pdf_url or "",
                }
            )
        return out
