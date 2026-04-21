# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AetherMind is an agentic research and report generator. Full build plan: `.cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md`. Read it before starting any phase.

**Current status:** Phase 2 complete — LLM gateway (`llm/client.py`, `llm/router.py`), embeddings module (`embeddings/client.py`), 28 tests passing. Next: Phase 3 (schemas + db_layer) or Phase 4 (tool_stubs).

## Environment

- **Backend:** Python 3.12, managed via `uv` (never use pip directly)
- **Frontend:** Next.js 15 App Router

## Commands

```bash
# Backend
cd backend
uv run fastapi dev app/main.py           # dev server
uv run alembic upgrade head              # run migrations
uv run pytest tests/ -x                  # all tests, stop on first fail
uv run pytest tests/path/test_file.py::test_name  # single test
uv run python -m app.eval.harness        # offline eval runner

# Frontend
cd frontend
npm run dev
npm run build
npm run lint

# Full stack
docker-compose up --build   # api + frontend + chroma
docker-compose up chroma    # vector store only
```

## Architecture

### Agent Loop
`planner → researcher (fan-out via Send API) → synthesizer → critic → conditional edge → memory_writer`

- **Graph:** `backend/app/agent/graph.py` (LangGraph `StateGraph`)
- **State:** `AgentState` TypedDict in `backend/app/agent/state.py`
- **Checkpointer:** `SqliteSaver` (resume/time-travel)
- Parallel tool calls inside each researcher node via `asyncio.gather`
- Critic loop: rubric-scored; routes back to synthesizer (or researcher on evidence gaps) up to N times

### LLM Routing
All model assignments go through `backend/app/llm/router.py` via env keys — **never hardcode model strings elsewhere.** The router enforces an 8GB VRAM ceiling: local Ollama/sentence-transformers only for models that fit; anything larger routes to a small API model.

| Env key | Role |
|---|---|
| `MODEL_PLANNER`, `MODEL_SYNTH` | Frontier API (planner/synthesis — user-visible quality) |
| `MODEL_CRITIC_INNER`, `MODEL_PREF_EXTRACT` | Local 7B Q4 or mini API |
| `MODEL_CRITIC_FINAL`, `MODEL_ENTAILMENT`, `MODEL_EVAL_JUDGE` | Mini API |

`FORCE_API_FOR_HEAVY=true` disables all local inference (CI / no-GPU dev). `LOCALVRAM_MAX_GB=8` is the ceiling.

Two additional env keys added in Phase 2: `MODEL_SOURCE_SUMMARY`, `MODEL_TOOL_FORMAT` (router falls back gracefully when unset).

**Retry policy:** Uses LiteLLM's built-in `num_retries` (not tenacity) — LiteLLM correctly skips retries on `AuthenticationError`/`BadRequestError` and keeps semantics consistent across all providers.

### Memory (hybrid)
- **SQLite:** preferences, jobs, reports, claims, citations, feedback, agent traces
- **Chroma collections:** `memory_preferences`, `memory_reports` (persistent); `scratch_sources` (ephemeral per-job — deduped source embeddings across researchers)
- `planner` calls `memory.recall(topic)`; `memory_writer` persists after approval

### Tools
All tools implement `BaseTool` → `ToolResult { content, source: Source }`. Source IDs must be registered before the synthesizer can cite them (`backend/app/tools/base.py`).

### Guardrails
- Synthesizer may only cite registered source IDs — Pydantic validator enforces this
- Citation verifier: local small NLI cross-encoder if under VRAM budget, else mini API entailment + overlap heuristic
- Unverified claims flagged to critic; no evidence → "insufficient evidence" (never fabricate)

### API Surface
```
POST /research                 → { job_id }
GET  /research/{id}/stream     → SSE of LangGraph events
GET  /reports/{id}
GET  /reports/{id}/versions
POST /feedback                 → triggers memory update
GET/POST /memory/preferences
```

## Key Invariants (enforced by PreToolUse hook)

1. **Router authority** — model strings only in `router.py` or `.env`; never hardcoded elsewhere in `backend/app/`
2. **Embedding isolation** — `sentence_transformers` imports only inside `backend/app/embeddings/`; never imported directly in tools, agents, or API code
3. **Citation closure** — every tool registers a `Source`; synthesizer cites by ID; guardrails verify

Violations are blocked by the `PreToolUse` hook before the file is written.

## Docstring Policy (enforced by PostToolUse hook)

After every `Edit`/`Write` on a `.py` file, `.claude/hooks/check_docstrings.py` runs automatically via AST and emits a `systemMessage` warning for:

- Any `def`, `async def`, or `class` missing a docstring (single-expression stubs exempt)
- Imports of notable libraries (`langgraph`, `chromadb`, `sqlalchemy`, `anthropic`, `openai`, etc.) with no inline or preceding comment

Non-blocking — warns but does not prevent the write. Fix flagged items before moving on.

## Build Order

```
bootstrap ✅ → llm_gateway + vram_router + embeddings_module ✅ → schemas + db_layer
→ tool_stubs → langgraph_core + parallel_research + critic_loop
→ guardrails + memory_service → fastapi_endpoints → frontend_* → eval_harness → observability + tests
```

Use `/phase <id>` to implement any phase (IDs match todo ids in the plan file).

## Agents & Skills

| Agent | Purpose |
|---|---|
| `phase-implementer` | Implements a full phase end-to-end; runs tests |
| `invariant-auditor` | Read-only scan for the 3 invariant violations |
| `langgraph-specialist` | Phase 5 — StateGraph, Send API, checkpointer |
| `frontend-specialist` | Phase 8 — Next.js 15, SSE client, shadcn/ui |
| `eval-harness-specialist` | Phase 9 — LLM-as-judge, Ragas metrics, Langfuse |

| Skill | Purpose |
|---|---|
| `/phase <id>` | Implement a build phase |
| `/check-invariants` | Audit `backend/` for all 3 invariant violations |
| `/scaffold-tool <name>` | Scaffold a new `BaseTool` with Source registration pre-wired |
| `/vram-check` | Validate `router.py` + `.env` against the 8GB ceiling |