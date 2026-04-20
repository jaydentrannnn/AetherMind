---
name: scaffold-tool
description: Scaffolds a new AetherMind `BaseTool` under `backend/app/tools/` with JSON parameters, async `run`, and `ToolResult` + `Source` wiring for citation closure. Use when the user asks for `/scaffold-tool`, a new tool name (e.g. `arxiv_search`), or to add a tool stub following project conventions.
---

# AetherMind — scaffold one tool

The user supplies a **snake_case** tool name (e.g. `my_source`). Create `backend/app/tools/<name>.py` with this shape (adjust types, schema, and `SourceType` to the real use case):

```python
from uuid import uuid4

from ..schemas import ToolResult, Source, SourceType
from .base import BaseTool


class MySourceTool(BaseTool):
    name = "my_source"
    description = "TODO: describe what this tool does"

    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "TODO"},
        },
        "required": ["query"],
    }

    async def run(self, query: str) -> ToolResult:
        content = ""

        source = Source(
            id=str(uuid4()),
            type=SourceType.TODO,  # replace with the correct SourceType once defined in schemas
            url=None,
            title="TODO",
            snippet=content[:500],
        )

        return ToolResult(content=content, source=source)
```

## Rules

- Class name = **PascalCase** from snake_case (`my_source` → `MySourceTool`).
- **Invariant 3** — Never return content without a `Source`; register before the synthesizer can cite.
- **Invariant 1** — No hardcoded provider model strings in the tool file.
- **Invariant 2** — No `sentence_transformers` in tools; use `EmbeddingClient` from `backend/app/embeddings/` when needed.

## Package export

If `backend/app/tools/__init__.py` exists, add:

`from .<name> import <PascalCase>Tool`

Keep imports sorted to match the file’s existing style.
