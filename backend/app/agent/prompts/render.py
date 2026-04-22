"""Minimal Jinja prompt renderer for agent node templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class PromptRenderer:
    """Render prompt templates from the agent prompts directory."""

    def __init__(self) -> None:
        """Initialize a file-system Jinja environment for local templates."""
        template_dir = Path(__file__).resolve().parent
        # Templates are plain text prompts; autoescape remains disabled for txt/j2.
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(disabled_extensions=("j2", "txt")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, **context: Any) -> str:
        """Render one template by name using keyword context values."""
        return self._env.get_template(template_name).render(**context)


renderer = PromptRenderer()
