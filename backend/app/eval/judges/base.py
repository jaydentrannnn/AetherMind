"""Shared helpers for per-stage LLM judges.

Each per-stage judge is a thin wrapper around `score_with_rubric` that
constructs the stage-specific prompt and rubric schema and dispatches through
the router under a stage-specific task tag (e.g. ``planner_judge``). All tags
fall back to ``eval_judge`` in the router, so configuring only
``MODEL_EVAL_JUDGE`` is sufficient for a cheap-live setup.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.config import settings
from app.eval.judge import JudgeResult
from app.llm.router import Router, TaskTag, router as default_router


class StageJudge(Protocol):
    """Callable shape implemented by every stage judge for type-checkers."""

    async def __call__(self, **kwargs: object) -> JudgeResult:
        """Score one stage case and return a normalized judge result."""
        ...


def _judge_disabled(task: TaskTag) -> tuple[bool, str | None]:
    """Return whether the judge is disabled and a human-readable reason."""
    # Any of the env keys in the fallback chain is sufficient; we conservatively
    # report disabled only when MODEL_EVAL_JUDGE itself is unset, because every
    # stage-tag's chain bottoms out at eval_judge.
    if settings.MODEL_EVAL_JUDGE is None and getattr(settings, f"MODEL_{task.upper()}", None) is None:
        return True, f"{task} judge model is not configured"
    return False, None


async def score_with_rubric(
    *,
    task: TaskTag,
    prompt: str,
    rubric_schema: type[BaseModel],
    aggregate_fields: tuple[str, ...],
    llm_router: Router | None = None,
    disabled_reason: str | None = None,
) -> JudgeResult:
    """Run one stage judge call and normalize the rubric into a JudgeResult.

    Args:
        task: Router task tag for this stage judge.
        prompt: Fully rendered user prompt.
        rubric_schema: Pydantic model the judge must populate.
        aggregate_fields: Field names of integer 0-5 scores to average.
        llm_router: Optional router override (eval harness injects one).
        disabled_reason: When set, returns a disabled JudgeResult immediately
            without making any LLM call.
    """
    if disabled_reason is not None:
        return JudgeResult(enabled=False, reason=disabled_reason)

    auto_disabled, auto_reason = _judge_disabled(task)
    if auto_disabled:
        return JudgeResult(enabled=False, reason=auto_reason)

    selected_router = llm_router or default_router
    rubric = await selected_router.structured(
        task,
        [{"role": "user", "content": prompt}],
        rubric_schema,
        metadata={"component": "eval_harness", "task": task},
    )
    scores: list[int] = []
    for field_name in aggregate_fields:
        value = getattr(rubric, field_name, None)
        if isinstance(value, int):
            scores.append(value)
    aggregate = round(sum(scores) / len(scores), 3) if scores else None

    try:
        model = selected_router.resolve(task)
    except Exception:
        model = None

    # The eval JudgeResult schema stores rubric as a generic JudgeRubric so we
    # carry the stage-specific rubric as JSON-friendly extras via the reason
    # field. The aggregate score remains the primary numeric signal.
    return JudgeResult(
        enabled=True,
        model=model,
        rubric=None,
        aggregate=aggregate,
        reason=rubric.model_dump_json(),
    )
