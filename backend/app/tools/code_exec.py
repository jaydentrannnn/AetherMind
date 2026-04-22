"""Code execution tool stub for explicit opt-in phases."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.schemas import ToolResult
from app.tools.base import BaseTool


class CodeExecNotEnabledError(RuntimeError):
    """Raised when code execution is invoked before opt-in configuration."""


class CodeExecTool(BaseTool):
    """Stub implementation that blocks execution until explicitly enabled."""

    name = "code_exec"
    description = "Execute code snippets in a sandboxed environment."
    input_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "language": {"type": "string", "default": "python"},
        },
        "required": ["code"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        """Raise a clear configuration error for the phase-4 stub."""
        del kwargs
        if not settings.ENABLE_CODE_EXEC:
            raise CodeExecNotEnabledError(
                "code_exec is disabled. Set ENABLE_CODE_EXEC=true and configure "
                "CODE_EXEC_PROVIDER in a future phase to enable sandbox execution."
            )
        raise CodeExecNotEnabledError(
            "code_exec stub is active. Real execution backend is not implemented yet."
        )
