"""Task -> model router (plan §1b, §1c).

This module is the **single** authority for which model runs where. All raw
model strings live in ``.env`` and are read here. Consumers call
``router.chat("planner", ...)`` -- they never see a model string.

VRAM policy: local models (``ollama/...`` or ``sentence-transformers`` families)
must fit within LOCALVRAM_MAX_GB. We enforce this by an allowlist of known-safe
local model identifiers. When ``FORCE_API_FOR_HEAVY`` is true, no local models
are permitted for any task (CI / no-GPU dev mode).
"""

from __future__ import annotations

from typing import Any, Literal, get_args

from pydantic import BaseModel

from app.config import settings
from app.llm.client import ChatResponse, LLMClient, client as default_client

TaskTag = Literal[
    "planner",
    "synthesize",
    "critic_inner",
    "critic_final",
    "pref_extract",
    "source_summary",
    "entailment",
    "tool_format",
    "eval_judge",
]

VALID_TASKS: tuple[str, ...] = get_args(TaskTag)


class RouterConfigError(RuntimeError):
    """Raised when a required MODEL_* env var is missing or invalid."""


class VRAMViolation(RuntimeError):
    """Raised when a configured local model would exceed the 8GB ceiling."""


# Local models explicitly known to fit within LOCALVRAM_MAX_GB=8.
# Anything outside this set must be routed via a hosted API provider.
LOCAL_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Chat
        "ollama/qwen3.5:3b",
        "ollama/qwen3.5:7b",
        "ollama/qwen2.5:3b",
        "ollama/qwen2.5:7b",
        "ollama/llama3.2:3b",
        # Embeddings
        "ollama/nomic-embed-text",
        "ollama/bge-m3",
    }
)

# Fallback chain: if the primary env var is unset, try the next tag. Tasks at
# the start of a chain (planner, synthesize) have no fallback and will raise
# ``RouterConfigError`` when missing.
_FALLBACK: dict[str, str | None] = {
    "planner": None,
    "synthesize": None,
    "critic_inner": "critic_final",
    "critic_final": "synthesize",
    "pref_extract": "critic_inner",
    "source_summary": "pref_extract",
    "entailment": "critic_final",
    "tool_format": "critic_inner",
    "eval_judge": "critic_final",
}

_ENV_KEY: dict[str, str] = {
    "planner": "MODEL_PLANNER",
    "synthesize": "MODEL_SYNTH",
    "critic_inner": "MODEL_CRITIC_INNER",
    "critic_final": "MODEL_CRITIC_FINAL",
    "pref_extract": "MODEL_PREF_EXTRACT",
    "source_summary": "MODEL_SOURCE_SUMMARY",
    "entailment": "MODEL_ENTAILMENT",
    "tool_format": "MODEL_TOOL_FORMAT",
    "eval_judge": "MODEL_EVAL_JUDGE",
}


def _is_local(model: str) -> bool:
    return model.startswith("ollama/")


def _validate_local(model: str, *, task: str) -> None:
    if settings.FORCE_API_FOR_HEAVY and _is_local(model):
        raise RouterConfigError(
            f"Task {task!r} resolved to local model {model!r} but "
            "FORCE_API_FOR_HEAVY=true. Set "
            f"{_ENV_KEY[task]} to a hosted model (e.g. openai/gpt-5.4-mini)."
        )
    if _is_local(model) and model not in LOCAL_ALLOWLIST:
        raise VRAMViolation(
            f"Task {task!r} resolved to {model!r} which is not in the "
            f"<={settings.LOCALVRAM_MAX_GB}GB local allowlist. Allowed: "
            f"{sorted(LOCAL_ALLOWLIST)}"
        )


class Router:
    """Resolves task tags to model strings and delegates to ``LLMClient``."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._client = llm_client or default_client

    def resolve(self, task: TaskTag) -> str:
        if task not in VALID_TASKS:
            raise RouterConfigError(f"Unknown task tag: {task!r}")

        visited: list[str] = []
        current: str | None = task
        while current is not None:
            visited.append(current)
            env_key = _ENV_KEY[current]
            model = getattr(settings, env_key, None)
            if model:
                _validate_local(model, task=task)
                return model
            current = _FALLBACK[current]

        raise RouterConfigError(
            f"No model configured for task {task!r} (tried {visited}). "
            f"Set {_ENV_KEY[task]} in .env."
        )

    async def chat(
        self,
        task: TaskTag,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ChatResponse:
        model = self.resolve(task)
        metadata = dict(kwargs.pop("metadata", None) or {})
        metadata.setdefault("task", task)
        return await self._client.chat(messages, model=model, metadata=metadata, **kwargs)

    async def structured(
        self,
        task: TaskTag,
        messages: list[dict[str, Any]],
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        model = self.resolve(task)
        metadata = dict(kwargs.pop("metadata", None) or {})
        metadata.setdefault("task", task)
        return await self._client.structured(
            messages, model=model, schema=schema, metadata=metadata, **kwargs
        )


router = Router()
