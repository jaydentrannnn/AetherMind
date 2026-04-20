---
name: scaffold-tool
description: Scaffold a new AetherMind tool in backend/app/tools/ with correct BaseTool structure, Source registration boilerplate, and ToolResult return type — all three citation-closure invariants pre-wired. Usage: /scaffold-tool <tool_name>
argument-hint: <tool_name>
allowed-tools: Write Read
---

Create a new tool named **$ARGUMENTS** at `backend/app/tools/$ARGUMENTS.py`.

The file must follow this structure exactly — do not skip Source registration (Invariant 3):

```python
from uuid import uuid4
from ..schemas import ToolResult, Source, SourceType
from .base import BaseTool


class $1Tool(BaseTool):
    name = "$ARGUMENTS"
    description = "TODO: describe what this tool does"

    # JSON schema for LiteLLM function calling
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "TODO"}
        },
        "required": ["query"]
    }

    async def run(self, query: str) -> ToolResult:
        # TODO: implement
        content = ""

        source = Source(
            id=str(uuid4()),
            type=SourceType.TODO,  # replace with correct type
            url=None,
            title="TODO",
            snippet=content[:500],
        )

        return ToolResult(content=content, source=source)
```

After writing the file, also append an import line to `backend/app/tools/__init__.py` if it exists:
`from .$ARGUMENTS import $1Tool`

Substitute `$1` with the PascalCase version of `$ARGUMENTS` (e.g., `web_search` → `WebSearch`).
