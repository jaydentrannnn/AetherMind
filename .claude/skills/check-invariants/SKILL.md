---
name: check-invariants
description: Scan the entire backend/ tree for violations of the three AetherMind invariants — router authority (no hardcoded model strings outside allowed files), embedding isolation (no direct sentence_transformers imports outside backend/app/embeddings/), and citation closure (all tools register Sources). Safe to run at any time; read-only.
context: fork
agent: invariant-auditor
allowed-tools: Read Grep Glob
---

Run a full invariant audit on `backend/`. Check all three invariants:

1. **Router authority** — grep for `openai/gpt-5.4`, `openai/gpt-5.4-mini`, `ollama/`, `anthropic/claude-`, and embedding model IDs outside their allowlisted locations.
2. **Embedding isolation** — grep for `sentence_transformers` imports and direct Ollama embed endpoint calls outside `backend/app/embeddings/`.
3. **Citation closure** — verify all tools in `backend/app/tools/` return a `ToolResult` with a `Source`, and synthesizer only uses registered IDs.

Report violations with file paths and line numbers. If backend/ doesn't exist yet, report "No backend code to audit — greenfield."
