---
name: run-tests
description: Runs the AetherMind backend pytest suite (fail fast) and frontend lint (and build when appropriate). Use proactively after completing a phase, before commit, or when the user asks for `/run-tests` or CI parity checks.
---

# AetherMind — run tests

Execute from the **repository root** (monorepo root). If `backend/` or `frontend/` is missing, say so and skip that leg.

## Backend

When `backend/` exists and `backend/tests/` is present (or pytest is configured):

```bash
cd backend && uv run pytest tests/ -x --tb=short
```

If there is no test layout yet, note that and only run targeted checks the user asked for.

## Frontend

When `frontend/package.json` exists:

```bash
cd frontend && npm run lint
```

If the user is preparing a release or touched build config, also run:

```bash
cd frontend && npm run build
```

## Reporting

Echo a short summary: which commands ran, pass/fail, and the first failing test name (if any).

Do not start long-running dev servers unless the user asks.
