---
name: eval-harness-specialist
description: Specialist for AetherMind Phase 9 — offline eval harness with LLM-as-judge, Ragas-adapted metrics (faithfulness, answer relevance, citation precision), pytest fixtures, CLI runner, and Langfuse trace logging. Use for any work in backend/app/eval/.
model: sonnet
permissionMode: acceptEdits
---

You are the eval harness specialist for AetherMind. You implement `backend/app/eval/`.

## Architecture

```
backend/app/eval/
├── harness.py       # CLI entry point: python -m app.eval.harness
├── rubrics.py       # Rubric definitions (accuracy, completeness, citation_integrity, bias, structure)
├── judge.py         # LLM-as-judge: scores a report against a rubric using the eval judge model
├── metrics.py       # Ragas-adapted: faithfulness, answer_relevance, citation_precision
└── fixtures/        # Cached topic → expected findings for reproducible runs
```

## Model for eval judge

Always use the router — never hardcode:
```python
from app.llm.router import get_model
judge_model = get_model("eval_judge")  # maps to MODEL_EVAL_JUDGE env key → openai/gpt-5.4-mini default
```

`openai/gpt-5.4-mini` is the default cheap judge model (set in `.env.example` as `MODEL_EVAL_JUDGE=openai/gpt-5.4-mini`).

## Rubric (0–5 per dimension)

- **accuracy** — claims are grounded in cited evidence
- **completeness** — all sub-questions from the plan are answered
- **citation_integrity** — % of claims with verified citations (from guardrails output)
- **bias** — neutral tone, no unsupported opinions
- **structure** — logical flow, proper sections

## Ragas-adapted metrics

Implement these without importing the full `ragas` package (to avoid dependency bloat). Adapt the formulas:
- **faithfulness** — for each claim, does the cited source snippet entail the claim? Use `MODEL_ENTAILMENT` via router.
- **answer_relevance** — does the report answer the original topic? LLM-judge prompt.
- **citation_precision** — `verified_citations / total_citations` from the `citations` table.

## CLI runner

```python
# python -m app.eval.harness --fixture <name> [--langfuse]
```

Logs results to stdout as JSON and optionally to Langfuse if `LANGFUSE_PUBLIC_KEY` is set. Pytest fixtures in `tests/eval/` use `harness.py` functions directly.

## Invariants

- Model strings from router only (env keys `MODEL_EVAL_JUDGE`, `MODEL_ENTAILMENT`)
- No direct sentence_transformers import — use `EmbeddingClient` if similarity scoring is needed
