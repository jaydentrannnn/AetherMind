"""PDF extraction tool using PyMuPDF only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz
import httpx

from app.schemas import ToolResult
from app.tools.base import BaseTool


class PdfLoaderTool(BaseTool):
    """Load PDF text by URL or local path without dedup side effects."""

    name = "pdf_loader"
    description = "Extract text from a PDF using PyMuPDF."
    input_schema = {
        "type": "object",
        "properties": {
            "path_or_url": {"type": "string"},
            "max_pages": {"type": "integer", "minimum": 1, "default": 10},
        },
        "required": ["path_or_url"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        """Extract plain text from PDF pages and register one source."""
        path_or_url = str(kwargs["path_or_url"])
        max_pages = int(kwargs.get("max_pages", 30))
        text_by_page = await self._load_text(path_or_url, max_pages)
        content = (
            "\n\n".join(text_by_page) if text_by_page else "No extractable text in PDF."
        )
        source = self._source_registry.create(
            source_type="pdf",
            title=f"PDF: {path_or_url}",
            url_or_doi=path_or_url,
            snippet=text_by_page[0] if text_by_page else None,
            metadata={"path_or_url": path_or_url, "pages_extracted": len(text_by_page)},
        )
        return ToolResult(content=content, source=source)

    async def _load_text(self, path_or_url: str, max_pages: int) -> list[str]:
        """Read a PDF and return per-page text chunks."""
        if path_or_url.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(path_or_url)
                response.raise_for_status()
            return self._extract_from_bytes(response.content, max_pages)
        return self._extract_from_path(path_or_url, max_pages)

    def _extract_from_path(self, path: str, max_pages: int) -> list[str]:
        """Extract text from a local PDF path."""
        pdf_path = Path(path)
        with fitz.open(pdf_path) as doc:
            return self._extract_from_doc(doc, max_pages)

    def _extract_from_bytes(self, data: bytes, max_pages: int) -> list[str]:
        """Extract text from PDF bytes."""
        with fitz.open(stream=data, filetype="pdf") as doc:
            return self._extract_from_doc(doc, max_pages)

    def _extract_from_doc(self, doc: fitz.Document, max_pages: int) -> list[str]:
        """Extract page text from an opened PyMuPDF document."""
        out: list[str] = []
        page_limit = min(max_pages, len(doc))
        for page_idx in range(page_limit):
            text = doc[page_idx].get_text("text").strip()
            if text:
                out.append(f"[Page {page_idx + 1}]\n{text}")
        return out
