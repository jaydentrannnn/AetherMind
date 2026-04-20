---
name: check-invariants
description: Read-only scan of `backend/` for AetherMind invariant violations — router authority, embedding isolation, and citation closure. Use proactively after significant backend edits, before merge, or when the user asks for an invariant audit or `/check-invariants`.
---

# AetherMind — invariant audit

Do **not** edit files. Scan `backend/` and report precise violations (path + line + short reason).

## Invariant 1 — Router authority

Allowed **only** in: `backend/app/llm/router.py`, `backend/app/llm/client.py`, `backend/app/config.py`, `backend/app/embeddings/` (embedding model ids), and any `.env*`.

Elsewhere, flag matches for (grep / ripgrep), excluding those paths:

- `openai/gpt-5.4`, `openai/gpt-5.4-mini`
- `ollama/` model tags
- `anthropic/claude-`
- Embedding ids such as `BAAI/bge-`, `all-MiniLM`, `text-embedding-3-`, `nomic-embed-text`

## Invariant 2 — Embedding isolation

- `sentence_transformers` imports only under `backend/app/embeddings/`
- No raw `api/embeddings` / `/api/embeddings` Ollama embed calls outside `backend/app/embeddings/`

## Invariant 3 — Citation closure

- Each module in `backend/app/tools/` should return `ToolResult` with a `Source` (no “raw string only” returns).
- `backend/app/agent/nodes/synthesizer.py` must not bypass citation / source-registry rules.

## Output format

Use three sections **ROUTER**, **EMBEDDINGS**, **CITATIONS**, each `PASS` or bullet violations, then a one-line **SUMMARY**.

If `backend/` is missing or empty: `No backend code to audit — greenfield.`

Optional: align narrative with `.cursor/agents/invariant-auditor.md` when a stricter checklist is needed.
