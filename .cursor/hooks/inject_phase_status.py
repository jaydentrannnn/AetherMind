#!/usr/bin/env python3
"""sessionStart: inject build phase summary into additional_context (Cursor analogue of UserPromptSubmit hook)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _project_root() -> Path:
    for key in ("CURSOR_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        v = os.environ.get(key)
        if v:
            return Path(v)
    return Path.cwd()


def _parse_plan_ids(plan_text: str) -> tuple[list[str], list[str]]:
    pending: list[str] = []
    done: list[str] = []
    current_id: str | None = None
    for line in plan_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("- id:"):
            current_id = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("status:") and current_id:
            status = stripped.split(":", 1)[1].strip()
            if status == "pending":
                pending.append(current_id)
            elif status == "done":
                done.append(current_id)
            current_id = None
    return pending, done


def main() -> None:
    # Consume sessionStart input (ignored); keeps stdin drained.
    raw = sys.stdin.read()
    if raw.strip():
        try:
            json.loads(raw)
        except json.JSONDecodeError:
            pass

    plan = _project_root() / ".cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md"
    if not plan.is_file():
        print("{}")
        return

    try:
        text = plan.read_text(encoding="utf-8")
    except OSError:
        print("{}")
        return

    pending, done = _parse_plan_ids(text)
    if not pending and not done:
        print("{}")
        return

    lines = ["[AetherMind build status]"]
    if done:
        lines.append(f"  Completed phases: {', '.join(done)}")
    if pending:
        lines.append(f"  Pending phases:   {', '.join(pending)}")
    lines.append("  Next: implement the first pending phase in order. Run /phase <id> to start.")

    ctx = "\n".join(lines)
    print(json.dumps({"additional_context": ctx}))


if __name__ == "__main__":
    main()
