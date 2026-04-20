---
name: phase
description: Implement a named AetherMind build phase end-to-end. Delegates to the phase-implementer subagent in a worktree so main branch stays clean until the phase is verified. Usage: /phase <phase_id>
argument-hint: <phase_id>
context: fork
agent: phase-implementer
---

Implement AetherMind build phase: **$ARGUMENTS**

Read the plan at `.cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md` to find all todos for phase `$ARGUMENTS`. Implement them fully, enforce the three invariants, run tests, and report what was created and what tests passed.

Valid phase IDs (in order): bootstrap, llm_gateway, vram_router, embeddings_module, schemas, db_layer, tool_stubs, langgraph_core, parallel_research, critic_loop, guardrails, memory_service, fastapi_endpoints, frontend_new_research, frontend_report_view, frontend_memory, eval_harness, observability, tests, stretch.
