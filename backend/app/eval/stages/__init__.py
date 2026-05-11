"""Per-node eval stage runners and registry.

Each stage runner is an async callable that returns a :class:`StageReport`.
The :data:`STAGE_REGISTRY` mapping is the single dispatch table consumed by
the CLI in :mod:`app.eval.harness`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.eval.models import StageReport
from app.eval.stages.critic import run_critic_stage
from app.eval.stages.guardrails import run_guardrails_stage
from app.eval.stages.memory import run_memory_stage
from app.eval.stages.planner import run_planner_stage
from app.eval.stages.researcher import run_researcher_stage
from app.eval.stages.synthesizer import run_synth_stage

StageRunner = Callable[..., Awaitable[StageReport]]

STAGE_REGISTRY: dict[str, StageRunner] = {
    "planner": run_planner_stage,
    "researcher": run_researcher_stage,
    "synthesizer": run_synth_stage,
    "guardrails": run_guardrails_stage,
    "critic": run_critic_stage,
    "memory": run_memory_stage,
}

STAGE_NAMES: tuple[str, ...] = tuple(STAGE_REGISTRY.keys())

__all__ = ["STAGE_NAMES", "STAGE_REGISTRY", "StageRunner"]
