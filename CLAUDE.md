# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AetherMind is a **greenfield** agentic research and report generator. The build plan lives at `.cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md` — read it before starting any phase. Nothing is implemented yet; all structure below is the target architecture.

## Environment

- **Conda env:** `aethermind` (activated automatically by VSCode terminal per `.vscode/settings.json`)
- **Backend:** Python 3.12, managed via `uv` (not pip directly)
- **Frontend:** Next.js 15 App Router, Node.js (version pinned in `frontend/package.json` once created)

## Commands

### Backend (once bootstrapped)
```bash
cd backend
uv run fastapi dev app/main.py          # dev server with hot reload
uv run alembic upgrade head             # run migrations
uv run pytest tests/ -x                 # run tests (stop on first failure)
uv run pytest tests/path/test_file.py::test_name  # single test
uv run python -m app.eval.harness       # offline eval runner
```

### Frontend (once bootstrapped)
```bash
cd frontend
npm run dev        # Next.js dev server
npm run build      # production build
npm run lint       # ESLint
```

### Docker (full stack)
```bash
docker-compose up --build   # API + frontend + Chroma + optional Langfuse
docker-compose up chroma    # just the vector store
```

## Architecture

### Agent Loop
`plan → (parallel tool calls per sub-question) → draft → critic (rubric-scored) → revise up to N times → finalize → memory-write`

LangGraph `StateGraph` in `backend/app/agent/graph.py`. State is `AgentState` (TypedDict in `state.py`). Checkpointer: `SqliteSaver` for resume/time-travel.

Nodes: `planner` → `researcher` (fan-out via Send API) → `synthesizer` → `critic` → conditional edge (revise or approve) → `memory_writer`.

### LLM Routing (critical constraint)
The router (`backend/app/llm/router.py`) enforces an **8GB VRAM ceiling** for local models. Every task has an env-keyed model assignment:

| Env key | Default role |
|---|---|
| `MODEL_PLANNER`, `MODEL_SYNTH` | Frontier API (Sonnet / GPT-4.1) |
| `MODEL_CRITIC_INNER`, `MODEL_PREF_EXTRACT` | Local Ollama 7B Q4 or mini API |
| `MODEL_CRITIC_FINAL`, `MODEL_ENTAILMENT`, `MODEL_EVAL_JUDGE` | Mini API |

`FORCE_API_FOR_HEAVY=true` disables all local inference (use in CI/no-GPU dev). `LOCALVRAM_MAX_GB=8` is the ceiling. Never load 14B+ models locally.

### Memory (hybrid)
- **SQLite** (structured): preferences, research jobs, reports, claims, citations, feedback, agent traces
- **Chroma** (semantic): `memory_preferences`, `memory_reports`, `scratch_sources` (per-job deduped source embeddings)
- Recall happens in `planner`; writes happen in `memory_writer`

### Tools
All tools implement `BaseTool` with JSON schema for LiteLLM function calling. Returns `ToolResult { content, source: Source }` — source IDs must be registered before synthesizer can cite them.

- `web_search` — Tavily (primary), Brave (fallback)
- `arxiv_search` — `arxiv` pypi package
- `pdf_loader` — `pymupdf` only (no LLM in this step); chunks → `scratch_sources`
- `code_exec` — E2B sandbox (remote); local subprocess is opt-in only
- `fetch_url` — `httpx` + readability-lxml

### Guardrails
- Synthesizer can only cite source IDs registered in the source registry — Pydantic validator enforces this
- Citation verifier: small local cross-encoder NLI (if VRAM allows) or mini API entailment + overlap heuristic
- Unverified claims flagged → critic; no evidence → "insufficient evidence" (no fabrication)

### API Surface
```
POST /research                   → { job_id }
GET  /research/{job_id}/stream   → SSE of LangGraph events
GET  /reports/{id}
GET  /reports/{id}/versions
POST /feedback                   → triggers memory update
GET/POST /memory/preferences
```

### Frontend Pages
- `/` — new research job (topic + depth/tools/sources options)
- `/reports/[id]` — live agent trace panel + Markdown report + CitationPopover + VersionDiff + FeedbackForm
- `/memory` — preferences table + allow/deny domain lists + semantic search over past reports

Key libs: `react-markdown` + `remark-gfm` for rendering, `diff-match-patch` for version diffs, shadcn/ui components.

## Build Order

Follow the phased order in the plan exactly:
1. bootstrap → 2. llm_gateway + vram_router + embeddings_module → 3. schemas + db_layer → 4. tool_stubs → 5. langgraph_core + parallel_research + critic_loop → 6. guardrails + memory_service → 7. fastapi_endpoints → 8. frontend_* → 9. eval_harness → 10. observability + tests

Use `/phase <id>` to start any phase (e.g. `/phase bootstrap`). Valid IDs match the todo ids in the plan file.

## Custom Agents & Skills

Project-scoped agents live in `.claude/agents/` and load automatically:

| Agent | Model | Purpose |
|---|---|---|
| `phase-implementer` | Opus | Implements a full phase end-to-end; runs tests |
| `invariant-auditor` | Haiku | Read-only scanner for the 3 invariants |
| `langgraph-specialist` | Sonnet | Phase 5 — StateGraph, Send API, checkpointer |
| `frontend-specialist` | Sonnet | Phase 8 — Next.js 15, SSE client, shadcn/ui |
| `eval-harness-specialist` | Sonnet | Phase 9 — LLM-as-judge, Ragas metrics, Langfuse |

Available skills (type `/` to see all):

| Skill | Purpose |
|---|---|
| `/phase <id>` | Implement a build phase via `phase-implementer` |
| `/check-invariants` | Audit `backend/` for all 3 invariant violations |
| `/run-tests` | Run `uv run pytest tests/ -x` + `npm run lint` |
| `/scaffold-tool <name>` | Scaffold a new `BaseTool` with Source registration pre-wired |
| `/vram-check` | Validate router.py + .env against the 8GB ceiling |

A `PreToolUse` hook blocks any `Edit`/`Write` to `backend/app/` that hardcodes model strings or imports `sentence_transformers` outside their allowed locations — violations exit with an error before the file is written.

## Key Invariants

- The router is the single authority for which model runs where — never hardcode model strings outside `router.py` or env vars
- All embeddings go through `backend/app/embeddings/` — never import sentence-transformers or call Ollama embed directly elsewhere
- Source citation is a closed system: register in tool → cite by ID in synthesizer → verify in guardrails
- Chroma collection `scratch_sources` is ephemeral per-job; `memory_*` collections are persistent
