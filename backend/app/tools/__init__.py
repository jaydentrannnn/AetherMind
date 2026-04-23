"""Tool exports for researcher nodes."""

__all__ = [
    "ArxivSearchTool",
    "BaseTool",
    "CodeExecNotEnabledError",
    "CodeExecTool",
    "FetchUrlTool",
    "PdfLoaderTool",
    "SourceRegistry",
    "ToolConfigError",
    "WebSearchTool",
]


def __getattr__(name: str):
    """Lazily import tool classes to avoid optional dependency import errors."""
    if name in {"BaseTool", "SourceRegistry"}:
        from app.tools.base import BaseTool, SourceRegistry

        return {"BaseTool": BaseTool, "SourceRegistry": SourceRegistry}[name]
    if name in {"CodeExecNotEnabledError", "CodeExecTool"}:
        from app.tools.code_exec import CodeExecNotEnabledError, CodeExecTool

        return {"CodeExecNotEnabledError": CodeExecNotEnabledError, "CodeExecTool": CodeExecTool}[name]
    if name == "FetchUrlTool":
        from app.tools.fetch_url import FetchUrlTool

        return FetchUrlTool
    if name == "PdfLoaderTool":
        from app.tools.pdf_loader import PdfLoaderTool

        return PdfLoaderTool
    if name in {"ToolConfigError", "WebSearchTool"}:
        from app.tools.web_search import ToolConfigError, WebSearchTool

        return {"ToolConfigError": ToolConfigError, "WebSearchTool": WebSearchTool}[name]
    if name == "ArxivSearchTool":
        from app.tools.arxiv_search import ArxivSearchTool

        return ArxivSearchTool
    raise AttributeError(name)
