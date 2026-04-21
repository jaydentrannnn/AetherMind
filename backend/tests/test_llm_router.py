"""Tests for ``app.llm.router`` -- task tag -> model resolution + VRAM policy."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.llm.client import ChatResponse, LLMClient, Usage
from app.llm.router import (
    LOCAL_ALLOWLIST,
    Router,
    RouterConfigError,
    VRAMViolation,
)


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all MODEL_* + FORCE_API_FOR_HEAVY before every test."""
    for key in (
        "MODEL_PLANNER",
        "MODEL_SYNTH",
        "MODEL_CRITIC_INNER",
        "MODEL_CRITIC_FINAL",
        "MODEL_PREF_EXTRACT",
        "MODEL_ENTAILMENT",
        "MODEL_EVAL_JUDGE",
        "MODEL_SOURCE_SUMMARY",
        "MODEL_TOOL_FORMAT",
    ):
        monkeypatch.setattr(settings, key, None)
    monkeypatch.setattr(settings, "FORCE_API_FOR_HEAVY", False)


def test_resolve_returns_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_PLANNER", "openai/gpt-5.4")
    assert Router().resolve("planner") == "openai/gpt-5.4"


def test_resolve_required_task_raises_when_unset() -> None:
    with pytest.raises(RouterConfigError, match="MODEL_PLANNER"):
        Router().resolve("planner")


def test_resolve_fallback_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """source_summary -> pref_extract -> critic_inner -> critic_final."""
    monkeypatch.setattr(settings, "MODEL_CRITIC_FINAL", "openai/gpt-5.4-mini")
    assert Router().resolve("source_summary") == "openai/gpt-5.4-mini"


def test_resolve_prefers_primary_over_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_ENTAILMENT", "openai/gpt-5.4-mini")
    monkeypatch.setattr(settings, "MODEL_CRITIC_FINAL", "openai/gpt-5.4")
    assert Router().resolve("entailment") == "openai/gpt-5.4-mini"


def test_force_api_for_heavy_rejects_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_CRITIC_INNER", "ollama/qwen3.5:7b")
    monkeypatch.setattr(settings, "FORCE_API_FOR_HEAVY", True)
    with pytest.raises(RouterConfigError, match="FORCE_API_FOR_HEAVY"):
        Router().resolve("critic_inner")


def test_unknown_ollama_model_raises_vram_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "MODEL_CRITIC_INNER", "ollama/qwen3.5:72b")
    with pytest.raises(VRAMViolation):
        Router().resolve("critic_inner")


def test_allowlisted_ollama_model_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = next(iter(LOCAL_ALLOWLIST))
    monkeypatch.setattr(settings, "MODEL_CRITIC_INNER", sample)
    assert Router().resolve("critic_inner") == sample


async def test_chat_delegates_with_task_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_PLANNER", "openai/gpt-5.4")
    fake_client = LLMClient()
    fake_client.chat = AsyncMock(  # type: ignore[method-assign]
        return_value=ChatResponse(content="ok", usage=Usage(), model="openai/gpt-5.4")
    )
    r = Router(llm_client=fake_client)
    await r.chat("planner", [{"role": "user", "content": "hi"}])
    kwargs = fake_client.chat.await_args.kwargs
    assert kwargs["model"] == "openai/gpt-5.4"
    assert kwargs["metadata"]["task"] == "planner"


async def test_chat_preserves_caller_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_PLANNER", "openai/gpt-5.4")
    fake_client = LLMClient()
    fake_client.chat = AsyncMock(  # type: ignore[method-assign]
        return_value=ChatResponse(content="ok", usage=Usage(), model="openai/gpt-5.4")
    )
    r = Router(llm_client=fake_client)
    await r.chat(
        "planner",
        [{"role": "user", "content": "hi"}],
        metadata={"trace_id": "abc"},
    )
    md = fake_client.chat.await_args.kwargs["metadata"]
    assert md["task"] == "planner"
    assert md["trace_id"] == "abc"
