---
name: phase
description: Implements one AetherMind plan phase end-to-end from `.cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md`, enforces the three hard invariants, and runs tests. Use when the user runs `/phase`, names a phase id (e.g. bootstrap, langgraph_core), or asks to start or finish a build phase.
---

# AetherMind — implement one plan phase

When the user gives a **phase id** (or you infer it from context), implement that slice of the monorepo completely before moving on.

## Before coding

1. Read `.cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md` and locate every todo whose `id` matches the requested phase (and any dependencies called out in the plan for that phase).
2. Read `CLAUDE.md` for invariants and commands.
3. Optional: load `.cursor/agents/phase-implementer.md` and follow it as the system prompt when delegating via Task / a dedicated subagent.

## Three hard invariants (every change)

1. **Router authority** — No hardcoded provider model strings outside `backend/app/llm/router.py`, `backend/app/llm/client.py`, `backend/app/config.py`, `backend/app/embeddings/`, or `.env*`. Elsewhere use env keys and the router.
2. **Embedding isolation** — No `sentence_transformers` (or direct Ollama embed HTTP) outside `backend/app/embeddings/`.
3. **Citation closure** — Every tool returns `ToolResult` with a registered `Source`; synthesizer cites only registered IDs.

## After implementing

- Backend: `cd backend && uv run pytest tests/ -x`
- Frontend (if touched): `cd frontend && npm run lint && npm run build`
- Report what shipped, what passed, and what is intentionally deferred.

## Valid phase ids (plan order)

`bootstrap`, `llm_gateway`, `vram_router`, `embeddings_module`, `schemas`, `db_layer`, `tool_stubs`, `langgraph_core`, `parallel_research`, `critic_loop`, `guardrails`, `memory_service`, `fastapi_endpoints`, `frontend_new_research`, `frontend_report_view`, `frontend_memory`, `eval_harness`, `observability`, `tests`, `stretch`
