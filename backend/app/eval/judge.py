"""LLM-as-judge adapter for offline eval runs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.config import settings
from app.llm.router import Router, router as default_router


class JudgeRubric(BaseModel):
    """Rubric scores returned by the eval-judge model."""

    accuracy: int = Field(ge=0, le=5)
    completeness: int = Field(ge=0, le=5)
    citation_integrity: int = Field(ge=0, le=5)
    bias: int = Field(ge=0, le=5)
    structure: int = Field(ge=0, le=5)
    reasoning: str = ""


class JudgeResult(BaseModel):
    """Normalized LLM-judge output attached to eval results."""

    enabled: bool
    model: str | None = None
    rubric: JudgeRubric | None = None
    aggregate: float | None = None
    reason: str | None = None


def _aggregate_rubric(rubric: JudgeRubric) -> float:
    """Compute the mean 0-5 score across rubric dimensions."""
    total = (
        rubric.accuracy
        + rubric.completeness
        + rubric.citation_integrity
        + rubric.bias
        + rubric.structure
    )
    return round(total / 5.0, 3)


def _render_judge_prompt(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    metric_snapshot: dict[str, float],
) -> str:
    """Render the user prompt consumed by the eval_judge task."""
    context_blob = "\n\n".join(f"- {ctx}" for ctx in contexts) if contexts else "- (none)"
    return (
        "Evaluate the answer using this rubric (0-5 each): "
        "accuracy, completeness, citation_integrity, bias, structure.\n\n"
        f"Question:\n{question}\n\n"
        f"Answer:\n{answer}\n\n"
        f"Retrieved context:\n{context_blob}\n\n"
        "Deterministic metrics snapshot:\n"
        f"- faithfulness: {metric_snapshot['faithfulness']}\n"
        f"- answer_relevance: {metric_snapshot['answer_relevance']}\n"
        f"- citation_precision: {metric_snapshot['citation_precision']}\n\n"
        "Return strict JSON for the rubric schema."
    )


class EvalJudge:
    """Judge facade that routes LLM eval calls through task tag `eval_judge`."""

    def __init__(self, *, llm_router: Router | None = None) -> None:
        """Store router dependency for structured judge calls."""
        self._router = llm_router or default_router

    @staticmethod
    def is_configured() -> bool:
        """Return whether a judge model is configured in settings."""
        return bool(settings.MODEL_EVAL_JUDGE)

    async def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
        metric_snapshot: dict[str, float],
        disabled_reason: str | None = None,
    ) -> JudgeResult:
        """Score one eval case with LLM-as-judge or return deterministic fallback."""
        if disabled_reason is not None:
            return JudgeResult(enabled=False, reason=disabled_reason)

        if not self.is_configured():
            return JudgeResult(enabled=False, reason="MODEL_EVAL_JUDGE is not configured")

        prompt = _render_judge_prompt(
            question=question,
            answer=answer,
            contexts=contexts,
            metric_snapshot=metric_snapshot,
        )
        rubric = await self._router.structured(
            "eval_judge",
            [{"role": "user", "content": prompt}],
            JudgeRubric,
            metadata={"component": "eval_harness"},
        )
        model: str | None = None
        try:
            model = self._router.resolve("eval_judge")
        except Exception:
            model = None
        return JudgeResult(enabled=True, model=model, rubric=rubric, aggregate=_aggregate_rubric(rubric))


def judge_result_to_dict(result: JudgeResult) -> dict[str, Any]:
    """Serialize judge output into JSON-friendly primitives."""
    payload = result.model_dump()
    if result.rubric is not None:
        payload["rubric"] = result.rubric.model_dump()
    return payload
