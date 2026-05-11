# AetherMind

Autonomous research agent that takes a topic, decomposes it into sub-questions, gathers evidence in parallel (web, arXiv, PDFs, code execution), synthesizes a cited structured report, self-evaluates against a rubric, iterates, and persists long-term memory of your preferences and past research.

Built with **LangGraph** for orchestration, **LiteLLM** for multi-provider inference, **FastAPI** for the backend, and **Next.js 15** for the frontend.

## Architecture

```
                            ┌──────────────┐
                            │  Next.js UI  │
                            └──────┬───────┘
                                   │ REST + SSE
                            ┌──────▼───────┐
                            │   FastAPI     │
                            └──────┬───────┘
                                   │
                            ┌──────▼───────┐
                            │  LangGraph   │
                            │   Runtime    │
                            └──────┬───────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      │                            │                            │
┌─────▼─────┐  ┌─────────────────▼─────────────────┐  ┌──────▼──────┐
│  Planner  │  │     Parallel Researchers           │  │   Memory    │
│           │  │  (fan-out via Send API)             │  │  Service    │
└─────┬─────┘  └─────────────────┬─────────────────┘  └──────┬──────┘
      │                          │                           │
      │           ┌──────────────┼──────────────┐           │
      │           │              │              │           │
      │      ┌────▼───┐   ┌─────▼────┐  ┌─────▼────┐     │
      │      │  Web   │   │  arXiv   │  │   PDF    │     │
      │      │ Search │   │  Search  │  │  Loader  │     │
      │      └────────┘   └──────────┘  └──────────┘     │
      │                                                    │
      │         ┌────────────┐    ┌─────────────┐         │
      │         │Synthesizer │───►│ Guardrails  │         │
      │         └────────────┘    └──────┬──────┘         │
      │                                  │                │
      │                           ┌──────▼──────┐         │
      │                           │   Critic    │         │
      │                           └──────┬──────┘         │
      │                    revise ◄──────┘──────► approve  │
      │                                          │         │
      │                                   ┌──────▼──────┐  │
      │                                   │Memory Writer├──┘
      │                                   └──────┬──────┘
      │                                ┌─────────┼─────────┐
      │                          ┌─────▼────┐  ┌─▼────────┐
      │                          │  SQLite  │  │  Chroma   │
      │                          └──────────┘  └──────────┘
      │
┌─────▼────────────┐
│   Task Router    │
│  (8GB VRAM cap)  │
├──────────────────┤
│ Local (Ollama)   │
│ Frontier API     │
│ Mini API         │
└──────────────────┘
```

**Core loop:** planner &rarr; parallel tool calls &rarr; synthesize &rarr; guardrails &rarr; critic (rubric-scored) &rarr; revise up to N &rarr; finalize &rarr; memory write.

## Features

- **Agentic research loop** with automatic planning, evidence gathering, synthesis, and self-critique
- **Parallel research** via LangGraph's Send API — each sub-question runs its own researcher node with concurrent tool calls
- **Citation integrity guardrails** — every tool registers a `Source`; the synthesizer can only cite registered IDs; a verifier checks claims via overlap heuristic + LLM entailment
- **Source policy** — per-user allow/deny domain lists enforced before synthesis
- **Hybrid long-term memory** — SQLite for structured preferences + Chroma for semantic recall of past reports and free-text preferences
- **Task-tagged LLM routing** — a single router resolves task &rarr; model, enforcing an 8 GB VRAM ceiling for local models
- **Offline eval harness** — LLM-as-judge + Ragas-style metrics (faithfulness, answer relevance, citation precision) with per-node stage evaluations
- **Observability** — Langfuse tracing on every graph node and tool call; structured logging via structlog
- **Live SSE streaming** — real-time agent trace events streamed to the frontend as research progresses
- **Version history** — every revision is persisted; the UI supports version diffs

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (StateGraph, Send API, SqliteSaver checkpointer) |
| LLM Gateway | LiteLLM (OpenAI, Anthropic, Google Vertex AI, Ollama) |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Frontend | Next.js 15 (App Router), React 18, Tailwind CSS, shadcn/ui |
| Vector Store | ChromaDB |
| Embeddings | sentence-transformers (bge-small, MiniLM) or hosted fallback |
| Observability | Langfuse, structlog |
| Testing | pytest, Playwright |
| Package Management | uv (backend), npm (frontend) |

## Repo Structure

```
AetherMind/
├── backend/
│   ├── pyproject.toml                  # uv-managed, Python 3.12+
│   ├── app/
│   │   ├── main.py                     # FastAPI entry, CORS, middleware, Langfuse wiring
│   │   ├── config.py                   # pydantic-settings — all env vars in one place
│   │   ├── api/
│   │   │   ├── router.py               # Aggregates all endpoint routers
│   │   │   ├── research.py             # POST /research, GET /research/{id}/stream (SSE)
│   │   │   ├── reports.py              # GET /reports/{id}, GET /reports/{id}/versions
│   │   │   ├── feedback.py             # POST /feedback
│   │   │   └── memory.py               # GET/POST /memory/preferences, GET /memory/search
│   │   ├── agent/
│   │   │   ├── graph.py                # LangGraph StateGraph assembly + checkpointer
│   │   │   ├── state.py                # AgentState TypedDict with annotated reducers
│   │   │   ├── depth.py                # Depth normalization (quick/standard/deep)
│   │   │   ├── nodes/
│   │   │   │   ├── planner.py          # Topic → sub-questions + tool selection
│   │   │   │   ├── researcher.py       # Fan-out per sub-question, parallel tool calls
│   │   │   │   ├── synthesizer.py      # Structured report generation with citations
│   │   │   │   ├── guardrails.py       # Source policy + citation verification
│   │   │   │   ├── critic.py           # Rubric-based scoring + revision directives
│   │   │   │   └── memory_writer.py    # Persist report + extract preference deltas
│   │   │   └── prompts/                # Jinja2 templates for each node
│   │   ├── tools/
│   │   │   ├── base.py                 # BaseTool interface + SourceRegistry
│   │   │   ├── web_search.py           # Tavily (Brave fallback)
│   │   │   ├── arxiv_search.py         # arXiv API
│   │   │   ├── pdf_loader.py           # pymupdf text + page-level chunking
│   │   │   ├── fetch_url.py            # httpx + readability
│   │   │   └── code_exec.py            # E2B sandbox (or local subprocess)
│   │   ├── llm/
│   │   │   ├── client.py               # LiteLLM async wrapper, retry, cost tracking
│   │   │   └── router.py               # Task → model resolution, VRAM policy
│   │   ├── embeddings/                 # Local sentence-transformers or hosted fallback
│   │   ├── memory/
│   │   │   ├── service.py              # Hybrid recall/write orchestrator
│   │   │   ├── sqlite_store.py         # Structured preferences, reports, feedback
│   │   │   └── vector_store.py         # Chroma-backed semantic memory
│   │   ├── guardrails/
│   │   │   ├── citation_verifier.py    # Overlap heuristic + LLM entailment
│   │   │   └── source_policy.py        # Allow/deny domain filtering
│   │   ├── eval/
│   │   │   ├── harness.py              # CLI runner: legacy fixtures + per-node stages
│   │   │   ├── judge.py                # LLM-as-judge scorer
│   │   │   ├── metrics.py              # Ragas-style deterministic metrics
│   │   │   ├── models.py               # Eval result schemas
│   │   │   ├── tracing.py              # Eval-specific Langfuse tracing
│   │   │   ├── fixtures/               # JSON test fixtures per stage
│   │   │   ├── judges/                 # Per-node judge implementations
│   │   │   ├── stages/                 # Per-node eval stage runners
│   │   │   └── stubs/                  # Deterministic LLM stubs for testing
│   │   ├── observability/
│   │   │   └── tracer.py               # Langfuse tracer with no-op fallback
│   │   └── schemas/                    # Pydantic models (Report, Source, Critique, etc.)
│   └── tests/
├── frontend/
│   ├── app/
│   │   ├── page.tsx                    # New research: topic input + advanced options
│   │   ├── reports/[id]/page.tsx       # Report viewer with live agent trace
│   │   └── memory/page.tsx             # Preferences editor + semantic search
│   ├── components/
│   │   ├── report/                     # ReportShell, AgentTrace, CitationPopover, VersionDiff
│   │   ├── research/                   # TopicForm, AdvancedOptions, RecentResearchList
│   │   ├── memory/                     # PreferencesTable, DomainListEditor, SemanticSearchPanel
│   │   └── shared/                     # TopNav, layout primitives
│   └── lib/
│       ├── api.ts                      # REST client + EventSource SSE helpers
│       └── types.ts                    # TypeScript type definitions
├── docker-compose.yml                  # api, frontend, chroma, langfuse, langfuse-postgres
├── .env.example                        # All configuration keys with documentation
└── CLAUDE.md                           # AI assistant reference (commands, architecture, invariants)
```

## Quick Start

### Prerequisites

- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) for backend dependency management
- **Node.js 18+** and npm for the frontend
- **Docker** and Docker Compose (optional, for full-stack deployment)
- At least one LLM API key (OpenAI, Anthropic, or Google Vertex AI) for frontier tasks
- **Ollama** (optional) for local model inference

### 1. Clone and configure

```bash
git clone https://github.com/your-org/AetherMind.git
cd AetherMind
cp .env.example .env
# Edit .env with your API keys and model preferences
```

### 2. Run with Docker Compose (recommended)

```bash
docker-compose up --build
```

This starts:

| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| Next.js frontend | http://localhost:3000 |
| ChromaDB | http://localhost:8001 |
| Langfuse (optional) | http://localhost:3001 |

### 3. Run locally (development)

**Backend:**

```bash
cd backend
uv sync                                 # Install/update dependencies
uv run alembic upgrade head             # Run database migrations
uv run fastapi dev app/main.py          # Start dev server on :8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev                             # Start dev server on :3000
```

**Vector store:**

```bash
docker-compose up chroma                # ChromaDB on :8001
```

### 4. Verify

```bash
curl http://localhost:8000/healthz
# → {"status": "ok"}
```

## Configuration

All configuration is managed through environment variables. Copy `.env.example` to `.env` and fill in the values.

### API Keys

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes* | OpenAI API key for frontier models |
| `ANTHROPIC_API_KEY` | No | Anthropic API key (alternative provider) |
| `VERTEXAI_PROJECT` | No | Google Cloud project for Vertex AI / Gemini |
| `TAVILY_API_KEY` | Yes | Web search tool |
| `BRAVE_API_KEY` | No | Fallback web search |
| `E2B_API_KEY` | No | Remote code execution sandbox |

*At least one frontier LLM provider key is required for planner/synthesizer tasks.

### Model Routing

The task-tagged router (`backend/app/llm/router.py`) is the single authority for which model runs where. Configure per-task models via environment variables:

| Variable | Task | Typical Assignment |
|---|---|---|
| `MODEL_PLANNER` | Topic decomposition | `openai/gpt-5.4` |
| `MODEL_SYNTH` | Report synthesis | `openai/gpt-5.4` |
| `MODEL_CRITIC_INNER` | Inner critic loop | `ollama/qwen3.5:7b` |
| `MODEL_CRITIC_FINAL` | Final critic gate | `openai/gpt-5.4-mini` |
| `MODEL_PREF_EXTRACT` | Preference extraction | `ollama/qwen3.5:7b` |
| `MODEL_ENTAILMENT` | Citation entailment | `openai/gpt-5.4-mini` |
| `MODEL_EVAL_JUDGE` | Eval harness judge | `openai/gpt-5.4-mini` |
| `MODEL_SOURCE_SUMMARY` | Source summarization | Falls back to `MODEL_PREF_EXTRACT` |
| `MODEL_TOOL_FORMAT` | Tool output formatting | Falls back to `MODEL_CRITIC_INNER` |

### VRAM Policy

| Variable | Default | Description |
|---|---|---|
| `LOCALVRAM_MAX_GB` | `8` | Maximum local GPU memory budget |
| `FORCE_API_FOR_HEAVY` | `false` | Set `true` for CI/no-GPU — forces all tasks to hosted APIs |

Local models (Ollama) are validated against an allowlist of models known to fit within the VRAM ceiling. Models outside the allowlist are rejected at startup with a clear error message.

### Embeddings

| Variable | Default | Description |
|---|---|---|
| `EMBEDDINGS_PROVIDER` | `sentence-transformers` | `sentence-transformers` or `openai` |
| `EMBEDDINGS_MODEL` | `BAAI/bge-small-en-v1.5` | Model name for the chosen provider |

### Observability

| Variable | Description |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | Langfuse project secret key |
| `LANGFUSE_HOST` | Langfuse host URL (defaults to cloud) |

When Langfuse keys are set, every graph node, tool call, and eval run is traced automatically. When absent, all tracing degrades to no-ops with zero runtime impact.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/research` | Start a new research job. Body: `{ topic, options }` &rarr; Returns `{ job_id }` |
| `GET` | `/research/{id}/stream` | SSE stream of live agent events (plan, tool calls, drafts, critiques) |
| `GET` | `/reports/{id}` | Fetch a completed report |
| `GET` | `/reports/{id}/versions` | List all revision versions of a report |
| `POST` | `/feedback` | Submit feedback on a report. Body: `{ report_id, comment, accept }` |
| `GET` | `/memory/preferences` | Retrieve user preferences and domain lists |
| `POST` | `/memory/preferences` | Update user preferences and domain lists |
| `GET` | `/memory/search?q=...` | Semantic search over past reports and memory |
| `GET` | `/healthz` | Health check |

## Agent Graph

The LangGraph `StateGraph` is assembled in `backend/app/agent/graph.py`:

```
START → planner → [fan-out] → researcher(s) → synthesizer → guardrails → critic
                                                                            │
                              ┌─────── revise (if score < threshold) ◄──────┘
                              │                                             │
                              └──► synthesizer / researcher                 │
                                                                            │
                                                              approve ──► memory_writer → END
```

**Key behaviors:**

- **Planner** decomposes the topic into 3-7 sub-questions, selects tools per sub-question, and injects user preferences from memory recall.
- **Researcher** (fan-out) runs one node per sub-question via LangGraph's `Send` API. Within each researcher, tools execute concurrently via `asyncio.gather`.
- **Synthesizer** produces a structured `Report` (Pydantic) with per-claim citation IDs referencing registered sources.
- **Guardrails** enforce source policy (allow/deny domains) and verify citation integrity via overlap heuristic + LLM entailment.
- **Critic** scores the draft against a rubric (accuracy, completeness, citation integrity, bias, structure). Routes back for revision or forward to finalization.
- **Memory Writer** persists the report, extracts preference deltas from feedback, and stores embeddings for future semantic recall.
- **Checkpointer** — `AsyncSqliteSaver` enables resume, time-travel, and human-in-the-loop interrupts.

State uses annotated reducers for `findings` (merge by sub-question ID) and `sources` (deduplicate by URL/DOI).

## Tools

All tools implement `BaseTool` and return `ToolResult { content, source: Source }`. Sources are registered in `SourceRegistry` before the synthesizer can cite them.

| Tool | Backend | Description |
|---|---|---|
| `web_search` | Tavily API (Brave fallback) | Web search with snippets and URLs |
| `arxiv_search` | `arxiv` Python package | Academic paper metadata + PDF URLs |
| `pdf_loader` | pymupdf | Text extraction + page-level chunking |
| `fetch_url` | httpx + readability-lxml | Arbitrary web page content extraction |
| `code_exec` | E2B sandbox (opt-in local subprocess) | Code execution for benchmarks/plots |

## Memory System

Hybrid architecture combining structured and semantic storage:

**SQLite** (structured):
- User preferences (key-value pairs)
- Research jobs, reports, claims, citations
- Source allow/deny domain lists
- Feedback history and agent traces

**ChromaDB** (semantic):
- `memory_preferences` — embedded free-text preferences for semantic matching
- `memory_reports` — past report summaries for cross-topic recall
- `scratch_sources` — per-job source deduplication during research

On each new job, the planner calls `memory.recall(topic)` which unions structured preferences + top-k semantic hits from Chroma. After job completion, `memory_writer` persists the report and extracts preference deltas from any user feedback.

## Guardrails

- **Source registry** — every tool result is registered with a UUID. The synthesizer must cite only registered IDs; Pydantic validators reject unknown IDs.
- **Citation verifier** — for each claim, the cited source snippet is checked against the claim via Jaccard overlap. If overlap is below threshold, an LLM entailment call determines support. Unverified claims are flagged to the critic.
- **Source policy** — per-user allow/deny domain lists. Violating sources are filtered out before synthesis.
- **Refusal path** — if a sub-question has no evidence meeting minimum confidence, the report states "insufficient evidence" instead of fabricating.

## Evaluation

### Online (in-loop)

The **critic** node scores every draft against a pluggable rubric (0-5 each dimension):
- Accuracy (evidence-grounded)
- Completeness (all sub-questions answered)
- Citation integrity (% claims verified)
- Bias / neutrality
- Structure / clarity

If the aggregate score is below threshold and revisions remain, the critic routes back for another pass.

### Offline (eval harness)

```bash
cd backend

# Legacy fixture-based eval (output-only)
uv run python -m app.eval.harness

# Per-node stage eval (planner, researcher, synthesizer, critic, guardrails, memory)
uv run python -m app.eval.harness --stage all

# Deterministic metrics only (no LLM judge calls)
uv run python -m app.eval.harness --stage all --deterministic-only

# With mock LLM stubs
uv run python -m app.eval.harness --stage all --mock-llm

# Save results to JSON
uv run python -m app.eval.harness --stage all --output-json results.json
```

**Metrics:** faithfulness, answer relevance, citation precision (Ragas-style deterministic) + LLM-as-judge aggregate scores. Results are traced to Langfuse when configured.

## Testing

```bash
# Backend — all tests, stop on first failure
cd backend
uv run pytest tests/ -x

# Single test
uv run pytest tests/test_agent_graph.py::test_name

# With coverage
uv run pytest tests/ --cov=app --cov-report=term-missing

# Frontend — lint
cd frontend
npm run lint

# Frontend — build check
npm run build

# Frontend — E2E (Playwright)
npm run test:e2e
```

## Development

### Code Quality

- **Backend:** ruff (linting + formatting), mypy (type checking)
- **Frontend:** ESLint + TypeScript strict mode

### Key Invariants

Three invariants are enforced across the codebase:

1. **Router authority** — model strings only appear in `router.py` or `.env`. No hardcoded model names anywhere else in `backend/app/`.
2. **Embedding isolation** — `sentence_transformers` imports only inside `backend/app/embeddings/`. All other modules go through the embeddings interface.
3. **Citation closure** — every tool registers a `Source`; the synthesizer cites by ID; guardrails verify. The chain is closed and auditable.

### Adding a New Tool

1. Create a class extending `BaseTool` in `backend/app/tools/`
2. Implement `run()` returning a `ToolResult` with a registered `Source`
3. Add the tool to the researcher's tool registry
4. Add the tool's JSON schema for function calling

## License

See [LICENSE](LICENSE) for details.
