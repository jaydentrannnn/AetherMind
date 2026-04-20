#!/usr/bin/env python3
"""preToolUse: block Write calls that violate AetherMind invariants (mirrors .claude/hooks/check_invariants.sh)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _project_root() -> Path:
    for key in ("CURSOR_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        v = __import__("os").environ.get(key)
        if v:
            return Path(v)
    return Path.cwd()


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


def _content(ti: dict) -> str:
    parts: list[str] = []
    for k in ("contents", "content", "new_string"):
        v = ti.get(k)
        if isinstance(v, str):
            parts.append(v)
    return "\n".join(parts)


def _is_backend_app(path: str) -> bool:
    n = _norm(path)
    return "backend/app/" in n or "backend\\app\\" in path


def _is_allowlisted(norm_path: str) -> bool:
    # Mirror .claude/hooks/check_invariants.sh: any path segment containing ".env"
    if ".env" in norm_path:
        return True
    markers = (
        "backend/app/llm/router.py",
        "backend/app/llm/client.py",
        "backend/app/config.py",
        "backend/app/embeddings/",
    )
    return any(m in norm_path for m in markers)


def _check(norm_path: str, content: str) -> list[str]:
    violations: list[str] = []

    if not _is_backend_app(norm_path):
        return violations

    if not _is_allowlisted(norm_path):
        patterns = [
            (r"openai/gpt-5\.4", "openai/gpt-5.4"),
            (r"openai/gpt-5\.4-mini", "openai/gpt-5.4-mini"),
            (r"ollama/", "ollama/"),
            (r"anthropic/claude-", "anthropic/claude-"),
            (r"BAAI/bge-", "BAAI/bge-"),
            (r"all-MiniLM", "all-MiniLM"),
            (r"text-embedding-3-", "text-embedding-3-"),
            (r"nomic-embed-text", "nomic-embed-text"),
        ]
        for regex, label in patterns:
            if re.search(regex, content):
                violations.append(
                    f"INVARIANT 1 (Router authority): pattern matching '{label}' in {norm_path}. "
                    "Model strings must only appear in router.py, client.py, config.py, embeddings/, or .env*."
                )

    if "backend/app/embeddings/" not in norm_path:
        if re.search(r"(from|import)\s+sentence_transformers", content):
            violations.append(
                f"INVARIANT 2 (Embedding isolation): sentence_transformers import in {norm_path}. "
                "Use EmbeddingClient from backend/app/embeddings/."
            )
        if re.search(r'"(api/embeddings|/api/embeddings)"', content):
            violations.append(
                f"INVARIANT 2 (Embedding isolation): Ollama embed endpoint string in {norm_path}. "
                "Use EmbeddingClient from backend/app/embeddings/."
            )

    return violations


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return

    tool_name = payload.get("tool_name") or ""
    if tool_name != "Write":
        print(json.dumps({"permission": "allow"}))
        return

    ti = _tool_input(payload)
    fp = _file_path(ti)
    content = _content(ti)
    norm = _norm(fp)

    violations = _check(norm, content)
    if violations:
        msg = "INVARIANT VIOLATION — write blocked.\n\n" + "\n\n".join(violations)
        print(
            json.dumps(
                {
                    "permission": "deny",
                    "user_message": msg[:2000],
                    "agent_message": msg[:8000],
                }
            )
        )
        return

    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()
