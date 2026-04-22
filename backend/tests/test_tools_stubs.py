"""Tests for phase-4 tool stubs."""

from __future__ import annotations

from pathlib import Path

import fitz
import httpx
import pytest
import respx

from app.config import settings
from app.tools import (
    ArxivSearchTool,
    CodeExecNotEnabledError,
    CodeExecTool,
    FetchUrlTool,
    PdfLoaderTool,
    SourceRegistry,
    ToolConfigError,
    WebSearchTool,
)


def _build_registry() -> SourceRegistry:
    """Return a fresh source registry for each test path."""
    return SourceRegistry()


async def test_web_search_returns_registered_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """web_search should register a source and return formatted lines."""
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")
    tool = WebSearchTool(source_registry=_build_registry())
    with respx.mock(assert_all_called=True) as mock:
        mock.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Example result",
                            "url": "https://example.com",
                            "content": "Snippet text",
                        }
                    ]
                },
            )
        )
        out = await tool.run(query="test query", max_results=1)
    assert "Example result" in out.content
    assert out.source.source_type == "web_search"
    assert tool._source_registry.get(out.source.id) is not None


async def test_web_search_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """web_search should fail fast when Tavily is not configured."""
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    tool = WebSearchTool(source_registry=_build_registry())
    with pytest.raises(ToolConfigError):
        await tool.run(query="missing key")


async def test_arxiv_search_registers_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """arxiv_search should return paper metadata and register source IDs."""
    tool = ArxivSearchTool(source_registry=_build_registry())

    def _fake_search(query: str, max_results: int) -> list[dict[str, str]]:
        """Return a deterministic fake arXiv payload."""
        del query, max_results
        return [
            {
                "id": "http://arxiv.org/abs/1234.5678",
                "title": "Sample arXiv Paper",
                "summary": "Abstract snippet",
                "pdf_url": "http://arxiv.org/pdf/1234.5678.pdf",
            }
        ]

    monkeypatch.setattr(tool, "_search_sync", _fake_search)
    out = await tool.run(query="attention is all you need")
    assert "Sample arXiv Paper" in out.content
    assert out.source.source_type == "arxiv"
    assert tool._source_registry.get(out.source.id) is not None


def _make_pdf(path: Path, text: str) -> None:
    """Create a one-page PDF for loader tests."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


async def test_pdf_loader_reads_local_pdf(tmp_path: Path) -> None:
    """pdf_loader should extract page text from local files."""
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path, "hello from local pdf")
    tool = PdfLoaderTool(source_registry=_build_registry())
    out = await tool.run(path_or_url=str(pdf_path), max_pages=2)
    assert "hello from local pdf" in out.content
    assert out.source.source_type == "pdf"
    assert tool._source_registry.get(out.source.id) is not None


async def test_pdf_loader_reads_url(tmp_path: Path) -> None:
    """pdf_loader should fetch PDF bytes when given an HTTP URL."""
    pdf_path = tmp_path / "remote.pdf"
    _make_pdf(pdf_path, "hello from remote pdf")
    tool = PdfLoaderTool(source_registry=_build_registry())
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://example.com/doc.pdf").mock(
            return_value=httpx.Response(200, content=pdf_path.read_bytes())
        )
        out = await tool.run(path_or_url="https://example.com/doc.pdf", max_pages=1)
    assert "hello from remote pdf" in out.content
    assert out.source.source_type == "pdf"


async def test_fetch_url_extracts_readable_text() -> None:
    """fetch_url should parse readability output and register source."""
    tool = FetchUrlTool(source_registry=_build_registry())
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://example.com/article").mock(
            return_value=httpx.Response(
                200,
                text="<html><head><title>X</title></head><body><article><h1>Title</h1><p>Body text.</p></article></body></html>",
                request=httpx.Request("GET", "https://example.com/article"),
            )
        )
        out = await tool.run(url="https://example.com/article")
    assert "Body text." in out.content
    assert out.source.source_type == "url"
    assert tool._source_registry.get(out.source.id) is not None


async def test_code_exec_stub_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """code_exec should remain disabled in this phase."""
    monkeypatch.setattr(settings, "ENABLE_CODE_EXEC", False)
    monkeypatch.setattr(settings, "CODE_EXEC_PROVIDER", "stub")
    tool = CodeExecTool(source_registry=_build_registry())
    with pytest.raises(CodeExecNotEnabledError, match="ENABLE_CODE_EXEC=true"):
        await tool.run(code="print('hi')", language="python")


def test_tool_function_schema_shape() -> None:
    """Base tool schema output should match LiteLLM function format."""
    tool = WebSearchTool(source_registry=_build_registry())
    schema = tool.function_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "web_search"


def test_source_registry_create_registers_uuid() -> None:
    """Source registry create helper should persist entries by generated id."""
    registry = _build_registry()
    source = registry.create(
        source_type="web_search",
        title="x",
        url_or_doi="https://example.com",
        snippet="snippet",
    )
    assert registry.get(source.id) is not None
    assert registry.all()
