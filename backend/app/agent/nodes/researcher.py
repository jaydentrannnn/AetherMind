"""Researcher node with parallel tool execution via asyncio.gather."""

from __future__ import annotations

import asyncio
from typing import Any

from app.agent.prompts.render import renderer
from app.agent.state import AgentState
from app.schemas import Finding, ToolResult
from app.tools import (
    ArxivSearchTool,
    BaseTool,
    FetchUrlTool,
    PdfLoaderTool,
    SourceRegistry,
    WebSearchTool,
)


def _build_tool_catalog(source_registry: SourceRegistry) -> dict[str, BaseTool]:
    """Create a tool-name to tool-instance mapping for one researcher run."""
    return {
        "web_search": WebSearchTool(source_registry=source_registry),
        "arxiv_search": ArxivSearchTool(source_registry=source_registry),
        "fetch_url": FetchUrlTool(source_registry=source_registry),
        "pdf_loader": PdfLoaderTool(source_registry=source_registry),
    }


def _tool_kwargs(tool_name: str, sub_question_text: str) -> dict[str, Any] | None:
    """Return default tool kwargs for a sub-question or None when unavailable."""
    if tool_name in {"web_search", "arxiv_search"}:
        return {"query": sub_question_text, "max_results": 3}
    return None


async def _safe_tool_run(tool: BaseTool, kwargs: dict[str, Any]) -> ToolResult | None:
    """Execute a tool and swallow failures to keep fan-out resilient."""
    try:
        return await tool.run(**kwargs)
    except Exception:
        return None


async def researcher_node(state: AgentState) -> AgentState:
    """Run selected tools concurrently for one sub-question branch."""
    sub_question = state["sub_question"]
    source_registry = SourceRegistry()
    catalog = _build_tool_catalog(source_registry)
    requested_tools = sub_question.suggested_tools or ["web_search", "arxiv_search"]

    tasks: list[asyncio.Task[ToolResult | None]] = []
    for tool_name in requested_tools:
        tool = catalog.get(tool_name)
        if tool is None:
            continue
        kwargs = _tool_kwargs(tool_name, sub_question.question)
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
