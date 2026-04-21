#!/usr/bin/env python3
"""Post-write hook: warn when Python functions, methods, or classes are missing docstrings,
and flag non-obvious library usages that lack an explanatory inline comment."""
import ast
import json
import sys

# Libraries whose non-trivial usage warrants inline comments when the call is not self-evident.
NOTABLE_LIBS = {
    "langgraph", "langchain", "chromadb", "sentence_transformers",
    "sqlalchemy", "alembic", "pydantic", "asyncio", "aiohttp",
    "anthropic", "openai", "ragas", "langfuse",
}


def _has_docstring(node: ast.AST) -> bool:
    """Return True if the given function/class/method node starts with a string literal."""
    return (
        bool(node.body)
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    )


def _is_trivial(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True for single-expression bodies that are self-documenting (e.g. @property stubs)."""
    return len(node.body) == 1 and isinstance(node.body[0], (ast.Return, ast.Pass, ast.Raise))


def check_missing_docstrings(tree: ast.AST) -> list[str]:
    """Walk the AST and return violation strings for any def/class missing a docstring."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _has_docstring(node) and not _is_trivial(node):
                kind = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                violations.append(f"  line {node.lineno}: `{kind} {node.name}()` — missing docstring")
        elif isinstance(node, ast.ClassDef):
            if not _has_docstring(node):
                violations.append(f"  line {node.lineno}: `class {node.name}` — missing docstring")
    return violations


def check_notable_imports(source: str, tree: ast.AST) -> list[str]:
    """Flag top-level imports from notable libraries so the author considers adding a comment."""
    lines = source.splitlines()
    warnings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            top = (node.module if isinstance(node, ast.ImportFrom) else None) or ""
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            lib = top.split(".")[0] if top else (names[0].split(".")[0] if names else "")
            if lib in NOTABLE_LIBS:
                lineno = node.lineno
                # Check if the preceding or same line has an inline comment — a proxy for "author explained it".
                prev_line = lines[lineno - 2].strip() if lineno >= 2 else ""
                same_line = lines[lineno - 1] if lineno >= 1 else ""
                if "#" not in same_line and not prev_line.startswith("#"):
                    warnings.append(
                        f"  line {lineno}: import of `{lib}` — consider a brief comment if its "
                        f"role or quirks are not obvious from context"
                    )
    return warnings


def main() -> None:
    """Entry point: read HOOK_TOOL_INPUT from stdin, check the written file, print JSON warnings."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
        filepath: str = data.get("file_path") or data.get("path") or ""
    except Exception:
        sys.exit(0)

    if not filepath.endswith(".py"):
        sys.exit(0)

    try:
        with open(filepath, encoding="utf-8") as fh:
            source = fh.read()
    except (OSError, UnicodeDecodeError):
        sys.exit(0)

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        sys.exit(0)

    docstring_issues = check_missing_docstrings(tree)
    import_hints = check_notable_imports(source, tree)

    parts: list[str] = []
    if docstring_issues:
        parts.append(
            f"Docstring check — {len(docstring_issues)} item(s) missing docstrings in "
            f"{filepath}:\n" + "\n".join(docstring_issues)
        )
    if import_hints:
        parts.append(
            "Library-clarity hints (non-blocking):\n" + "\n".join(import_hints)
        )

    if parts:
        print(json.dumps({"systemMessage": "\n\n".join(parts)}))


if __name__ == "__main__":
    main()
