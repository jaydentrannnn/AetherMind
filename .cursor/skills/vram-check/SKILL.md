---
name: vram-check
description: Read-only validation that `backend/app/llm/router.py` and `.env*` model assignments respect the 8GB VRAM policy and use plan-approved model ids. Use proactively after any change to `router.py`, `.env`, or `.env.example`, or when the user asks for `/vram-check`.
---

# AetherMind — VRAM / model assignment check

Read-only. Do not “fix” unless the user explicitly asks.

## Valid reference set (plan §11)

| Tier | Model | Approx VRAM |
|------|--------|----------------|
| Frontier API | `openai/gpt-5.4` | API |
| Mini API | `openai/gpt-5.4-mini` | API |
| Local chat | `ollama/qwen3.5:7b` (Q4) | ~4–5GB |
| Local chat (light) | `ollama/qwen3.5:3b` (Q4) | ~2GB |
| Embeddings (local) | `BAAI/bge-small-en-v1.5`, `all-MiniLM-L6-v2`, `ollama/nomic-embed-text` | <1GB |
| Embeddings (API) | `text-embedding-3-small` | API |

Treat **14B+ local chat** and other heavy local stacks as violations of the **8GB** ceiling unless routed to API via policy/env.

## Checks

1. **router** — If `backend/app/llm/router.py` exists, list every concrete model string; flag unknown or obviously oversized local models.
2. **env** — In `.env` / `.env.example` (if present), list `MODEL_*` and `EMBEDDINGS_MODEL`; flag values outside the table above or inconsistent with `CLAUDE.md`.
3. **Guards** — Confirm `.env.example` documents `FORCE_API_FOR_HEAVY` and `LOCALVRAM_MAX_GB=8` (or equivalent `LOCALVRAM_MAX_GB`).

## Report template

```text
VRAM CHECK
  router.py model references: ...
  .env MODEL_* / EMBEDDINGS_MODEL: ...
  Violations: none | (bulleted)
  FORCE_API_FOR_HEAVY in .env.example: yes/no
  LOCALVRAM_MAX_GB in .env.example: yes/no (value: ...)
```

If router and env files are absent: `No router.py or .env found — greenfield.`
