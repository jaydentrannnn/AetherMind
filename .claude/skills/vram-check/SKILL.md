---
name: vram-check
description: Validate that router.py and .env model assignments stay within the 8GB VRAM ceiling and use only the valid model names from the project plan. Run after any router.py or .env change. Read-only.
allowed-tools: Read Grep Glob
---

Audit `backend/app/llm/router.py` and any `.env*` files for VRAM compliance.

## Valid model assignments (from plan §11)

| Tier | Model | Approx VRAM |
|---|---|---|
| Frontier API | `openai/gpt-5.4` | none (API) |
| Mini API | `openai/gpt-5.4-mini` | none (API) |
| Local chat | `ollama/qwen3.5:7b` (Q4) | ~4–5GB |
| Local chat (light) | `ollama/qwen3.5:3b` (Q4) | ~2GB |
| Embeddings (local) | `BAAI/bge-small-en-v1.5`, `all-MiniLM-L6-v2`, `ollama/nomic-embed-text` | <1GB |
| Embeddings (API) | `text-embedding-3-small` | none (API) |

## Checks to perform

1. Read `backend/app/llm/router.py` (if it exists) — list every model string referenced. Flag any that are 14B+ local models (would exceed 8GB).
2. Read `.env` and `.env.example` — list all `MODEL_*` and `EMBEDDINGS_MODEL` values. Flag any not in the valid set above.
3. Confirm `FORCE_API_FOR_HEAVY` is defined in `.env.example`.
4. Confirm `LOCALVRAM_MAX_GB=8` is defined in `.env.example`.

## Report format

```
VRAM CHECK
  router.py model references: ...
  .env MODEL_* assignments: ...
  Violations: none / list
  FORCE_API_FOR_HEAVY defined: yes/no
  LOCALVRAM_MAX_GB defined: yes/no (value: X)
```

If neither file exists yet, report "No router.py or .env found — greenfield."
