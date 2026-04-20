#!/usr/bin/env python3
"""postToolUse: remind to run VRAM check after router edits (mirrors .claude/settings.json PostToolUse snippet)."""

from __future__ import annotations

import json
import sys


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _tool_input(payload: dict) -> dict:
    return payload.get("tool_input") or {}


def _file_path(ti: dict) -> str:
    return str(
        ti.get("file_path")
        or ti.get("path")
        or ti.get("target_file")
        or ""
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("{}")
        return

    if payload.get("tool_name") != "Write":
        print("{}")
        return

    fp = _file_path(_tool_input(payload))
    if "llm/router.py" in _norm(fp):
        msg = (
            "router.py was modified — run /vram-check to validate model assignments against the 8GB VRAM ceiling."
        )
        print(json.dumps({"additional_context": msg}))
        return

    print("{}")


if __name__ == "__main__":
    main()
