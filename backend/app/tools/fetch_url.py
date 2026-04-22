"""URL fetch + readability extraction tool."""

from __future__ import annotations

import re
from typing import Any

import httpx
from readability import Document

from app.schemas import ToolResult
from app.tools.base import BaseTool


class FetchUrlTool(BaseTool):
    """Fetch a webpage and extract readable content."""

    name = "fetch_url"
    description = "Fetch a URL and extract readable body text."
    input_schema = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        """Download and clean URL content for downstream synthesis."""
        url = str(kwargs["url"])
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "AetherMind/0.0.0 (+research-agent)"},
            )
            response.raise_for_status()

        readable = Document(response.text)
        summary_html = readable.summary(html_partial=True)
        text = self._html_to_text(summary_html)
        source = self._source_registry.create(
            source_type="url",
            title=readable.short_title() or url,
            url_or_doi=str(response.url),
            snippet=text[:500],
            metadata={"status_code": response.status_code},
        )
        return ToolResult(content=text, source=source)

    def _html_to_text(self, html: str) -> str:
        """Convert minimal HTML fragments to normalized plain text."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text
