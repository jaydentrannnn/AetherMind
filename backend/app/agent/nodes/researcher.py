"""Researcher node with parallel tool execution via asyncio.gather."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from app.agent.depth import normalize_depth, profile_for_depth
from app.agent.prompts.render import renderer

_log = logging.getLogger(__name__)
from app.agent.state import AgentState
from app.schemas import Finding, ToolResult
from app.tools.base import BaseTool, SourceRegistry

_URL_SCHEME_RE = re.compile(r"https?://[^\s)>\]}\"']+", re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/[^\s)>\]}\"']*)?\b",
    re.IGNORECASE,
)


def _rstrip_trailing_punctuation(value: str) -> str:
    """Remove common trailing punctuation from extracted URL-like tokens."""
    return value.rstrip(".,;:!?)>]}\"'")


def _extract_http_url(text: str) -> str | None:
    """Extract and normalize one HTTP(S) URL from freeform text."""
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.lower().startswith(("http://", "https://")):
        return _rstrip_trailing_punctuation(stripped)

    scheme_match = _URL_SCHEME_RE.search(stripped)
    if scheme_match:
        return _rstrip_trailing_punctuation(scheme_match.group(0))

    domain_match = _BARE_DOMAIN_RE.search(stripped)
    if not domain_match:
        return None
    domain = _rstrip_trailing_punctuation(domain_match.group(0))
    return f"https://{domain}"


def _extract_pdf_target(text: str) -> str | None:
    """Extract a likely PDF URL/path token from freeform text."""
    stripped = text.strip()
    if not stripped:
        return None

    url = _extract_http_url(stripped)
    if url and ".pdf" in url.lower():
        return url

    path_token = stripped.split()[0]
    if path_token.lower().endswith(".pdf"):
        return _rstrip_trailing_punctuation(path_token)
    return None


def _build_tool_catalog(source_registry: SourceRegistry) -> dict[str, BaseTool]:
    """Create a tool-name to tool-instance mapping for one researcher run."""
    from app.tools import ArxivSearchTool, FetchUrlTool, PdfLoaderTool, WebSearchTool

    return {
        "web_search": WebSearchTool(source_registry=source_registry),
        "arxiv_search": ArxivSearchTool(source_registry=source_registry),
        "fetch_url": FetchUrlTool(source_registry=source_registry),
        "pdf_loader": PdfLoaderTool(source_registry=source_registry),
    }


def _tool_kwargs(
    tool_name: str,
    sub_question_text: str,
    *,
    depth: str | None,
) -> dict[str, Any] | None:
    """Return default tool kwargs for a sub-question or None when unavailable."""
    profile = profile_for_depth(normalize_depth(depth))
    if tool_name in {"web_search", "arxiv_search"}:
        kwargs: dict[str, Any] = {
            "query": sub_question_text,
            "max_results": profile.search_max_results,
        }
        if tool_name == "web_search":
            kwargs["search_depth"] = profile.web_search_depth
        return kwargs
    if tool_name == "fetch_url":
        url = _extract_http_url(sub_question_text)
        if url is None:
            return None
        return {"url": url}
    if tool_name == "pdf_loader":
        pdf_target = _extract_pdf_target(sub_question_text)
        if pdf_target is None:
            return None
        return {"path_or_url": pdf_target}
    return None


async def _safe_tool_run(tool: BaseTool, kwargs: dict[str, Any]) -> ToolResult | None:
    """Execute a tool and swallow failures to keep fan-out resilient."""
    try:
        return await tool.run(**kwargs)
    except Exception as exc:
        _log.warning("Tool %s failed: %s", tool.name, exc)
        return None


async def researcher_node(state: AgentState) -> AgentState:
    """Run selected tools concurrently for one sub-question branch."""
    sub_question = state["sub_question"]
    source_registry = SourceRegistry()
    catalog = _build_tool_catalog(source_registry)
    requested_tools = sub_question.suggested_tools or ["web_search", "arxiv_search"]
    depth = normalize_depth(state.get("depth"))

    tasks: list[asyncio.Task[ToolResult | None]] = []
    for tool_name in requested_tools:
        tool = catalog.get(tool_name)
        if tool is None:
            continue
        kwargs = _tool_kwargs(tool_name, sub_question.question, depth=depth)
        if kwargs is None:
            continue
        tasks.append(asyncio.create_task(_safe_tool_run(tool, kwargs)))

    results = await asyncio.gather(*tasks) if tasks else []
    successful = [result for result in results if result is not None]
    evidence_lines = [result.content for result in successful]
    answer = renderer.render(
        "researcher.j2",
        topic=state["topic"],
        sub_question=sub_question,
        evidence=evidence_lines,
    )
    finding = Finding(
        sub_question_id=sub_question.id,
        answer=answer,
        evidence=evidence_lines,
        source_ids=[result.source.id for result in successful],
    )
    return {
        "findings": [finding],
        "sources": [result.source for result in successful],
    }
