# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AetherMind is an agentic research/report generator.  
Source of truth plan: `.cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md`.

**Current status:** Phase 8 complete. API endpoints, SSE streaming, frontend report UI, and all guardrails are implemented. **Next phase:** `eval_harness` / observability hardening.

## Coding Behavior

**Think before coding.** State assumptions explicitly. If multiple interpretations exist, present them — don't pick silently. If something is unclear, ask before implementing.

**Simplicity first.** Write the minimum code that solves the problem. No features beyond what was asked, no abstractions for single-use code, no error handling for impossible scenarios.

**Surgical changes.** Touch only what you must. Don't improve adjacent code, comments, or formatting. Match existing style. If your changes make imports or functions unused, remove only those — don't touch pre-existing dead code.

**Multi-step tasks:** state a brief plan with verifiable checks before starting (e.g. "1. Add validator → verify: test X passes").

## Environment

- **Backend:** Python 3.13, managed via `uv` (never use pip directly)
- **Frontend:** Next.js 15 App Router

## Commands

```bash
# Backend
cd backend
uv sync                                           # install/update deps
uv run fastapi dev app/main.py                    # dev server
uv run alembic upgrade head                       # run migrations
uv run pytest tests/ -x                           # all tests, stop on first fail
uv run pytest tests/path/test_file.py::test_name  # single test
uv run python -m app.eval.harness                 # offline eval runner

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
`planner → researcher (fan-out via Send API) → synthesizer → guardrails → critic → conditional edge → memory_writer`

- **Graph:** `backend/app/agent/graph.py` — `build_graph()` compiles the `StateGraph` with a `SqliteSaver` checkpointer at `AGENT_CHECKPOINT_PATH`
- **State:** `AgentState` TypedDict in `backend/app/agent/state.py`; `findings`/`sources` use annotated reducers (merge by ID, deduplicate by URL/DOI); `filtered_sources` is a plain (no-reducer) field written by guardrails and preferred by synthesizer
- **Fan-out:** `_fan_out_from_plan` issues one `Send("researcher", ...)` per `SubQuestion` in `state["plan"]`; each researcher branch runs its tools concurrently via `asyncio.gather`
- **Critic routing:** `_route_after_critic` reads `state["next_action"]`; if `"researcher"` it re-fans-out; otherwise routes to `"synthesizer"` or `"memory_writer"`; hard-stops at `AGENT_MAX_REVISIONS`
- **Prompts:** Jinja2 templates in `backend/app/agent/prompts/*.j2`, rendered by the `PromptRenderer` singleton (`renderer`) in `render.py`; researcher template receives actual `evidence` lines from tool outputs
- **Memory service:** `backend/app/memory/service.py` orchestrates SQLite + Chroma recall/write for planner and memory_writer

### LLM Routing
All model assignments go through `backend/app/llm/router.py` via env keys — **never hardcode model strings elsewhere.** Enforces 8GB VRAM ceiling.

| Env key | Role |
|---|---|
| `MODEL_PLANNER`, `MODEL_SYNTH` | Frontier API |
| `MODEL_CRITIC_INNER`, `MODEL_PREF_EXTRACT` | Local 7B Q4 or mini API |
| `MODEL_CRITIC_FINAL`, `MODEL_ENTAILMENT`, `MODEL_EVAL_JUDGE` | Mini API |

`FORCE_API_FOR_HEAVY=true` disables all local inference (CI / no-GPU dev). `LOCALVRAM_MAX_GB=8` is the ceiling.

**Retry policy:** LiteLLM's built-in `num_retries` — not tenacity. Correctly skips retries on `AuthenticationError`/`BadRequestError`.

### Memory (hybrid)
- **SQLite:** preferences, jobs, reports, claims, citations, feedback, agent traces
- **Chroma:** `memory_preferences`, `memory_reports` (persistent); `scratch_sources` (ephemeral per-job)
- `planner` calls `memory.recall(topic)`; `memory_writer` persists after approval

### Tools
All tools implement `BaseTool` → `ToolResult { content, source: Source }`. Source IDs are registered in `SourceRegistry` before the synthesizer can cite them (`backend/app/tools/base.py`). The synthesizer prompt receives `valid_source_ids` and is constrained to only cite those IDs.

### Guardrails
- `SourcePolicy.filter_sources` splits sources into allowed/violations before citation verification; allowed subset is stored in `filtered_sources` state and passed to the synthesizer on revision runs
- Citation verifier: overlap heuristic first, then mini API entailment fallback (`CitationVerifier` in `backend/app/guardrails/citation_verifier.py`)
- Unverified claims flagged to critic; no evidence → "insufficient evidence" (never fabricate)

### Jobs & SSE
`backend/app/api/jobs.py` — `JobManager` runs the graph (or deterministic fallback when `MODEL_PLANNER`/`MODEL_SYNTH` are unset). Each subscriber gets its own `asyncio.Queue` seeded from the replay buffer at connect time; `_emit` fans out to all live subscriber queues. Job status is `"completed"` on success or `"failed"` on exception.

### API Surface
```
POST /research                 → { job_id }
GET  /research/{id}/stream     → SSE of LangGraph events
GET  /reports/{id}
GET  /reports/{id}/versions
POST /feedback                 → triggers memory update
GET/POST /memory/preferences
GET  /memory/search
```

## Key Invariants (enforced by PreToolUse hook)

1. **Router authority** — model strings only in `router.py` or `.env`; never hardcoded elsewhere in `backend/app/`
2. **Embedding isolation** — `sentence_transformers` imports only inside `backend/app/embeddings/`
3. **Citation closure** — every tool registers a `Source`; synthesizer cites by ID; guardrails verify

Violations are blocked by the `PreToolUse` hook before the file is written.

## Docstring Policy (enforced by PostToolUse hook)

After every `Edit`/`Write` on a `.py` file, `.claude/hooks/check_docstrings.py` warns (non-blocking) for any `def`, `async def`, or `class` missing a docstring. Fix flagged items before moving on.

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
| `/phase <id>` | Implement a build phase (IDs match plan file) |
| `/check-invariants` | Audit `backend/` for all 3 invariant violations |
| `/scaffold-tool <name>` | Scaffold a new `BaseTool` with Source registration pre-wired |
| `/vram-check` | Validate `router.py` + `.env` against the 8GB ceiling |
