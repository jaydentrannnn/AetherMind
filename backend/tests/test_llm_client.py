"""Tests for ``app.llm.client`` -- the LiteLLM wrapper."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.llm.client import (
    ChatResponse,
    LLMClient,
    StructuredOutputError,
    Usage,
)


def _fake_response(content: str = "hello", model: str = "openai/gpt-test") -> MagicMock:
    """Build a mock mimicking a LiteLLM ``ModelResponse``."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    resp.model = model
    return resp


async def test_chat_returns_content() -> None:
    c = LLMClient()
    with patch("app.llm.client.acompletion", new=AsyncMock(return_value=_fake_response("ok"))):
        resp = await c.chat(
            [{"role": "user", "content": "hi"}], model="openai/gpt-test"
        )
    assert isinstance(resp, ChatResponse)
    assert resp.content == "ok"
    assert resp.usage.prompt_tokens == 10
    assert resp.usage.total_tokens == 15


async def test_chat_passes_ollama_api_base() -> None:
    """When model is ``ollama/*`` the client should inject api_base/keep_alive."""
    mock = AsyncMock(return_value=_fake_response("pong", model="ollama/qwen3.5:7b"))
    c = LLMClient()
    with patch("app.llm.client.acompletion", new=mock):
        await c.chat([{"role": "user", "content": "hi"}], model="ollama/qwen3.5:7b")
    kwargs = mock.call_args.kwargs
    assert kwargs["model"] == "ollama/qwen3.5:7b"
    assert "api_base" in kwargs
    assert "keep_alive" in kwargs


async def test_chat_forwards_tools_and_metadata() -> None:
    mock = AsyncMock(return_value=_fake_response())
    c = LLMClient()
    tools = [{"type": "function", "function": {"name": "x", "parameters": {}}}]
    with patch("app.llm.client.acompletion", new=mock):
        await c.chat(
            [{"role": "user", "content": "hi"}],
            model="openai/gpt-test",
            tools=tools,
            tool_choice="auto",
            max_tokens=42,
            metadata={"task": "planner"},
        )
    kwargs = mock.call_args.kwargs
    assert kwargs["tools"] == tools
    assert kwargs["tool_choice"] == "auto"
    assert kwargs["max_tokens"] == 42
    assert kwargs["metadata"] == {"task": "planner"}
    assert kwargs["num_retries"] >= 1


async def test_cost_callback_fires_with_task() -> None:
    captured: dict[str, Any] = {}

    def cb(usage: Usage, model: str, task: str | None) -> None:
        captured["usage"] = usage
        captured["model"] = model
        captured["task"] = task

    c = LLMClient(cost_callback=cb)
    with patch("app.llm.client.acompletion", new=AsyncMock(return_value=_fake_response())):
        await c.chat(
            [{"role": "user", "content": "hi"}],
            model="openai/gpt-test",
            metadata={"task": "synthesize"},
        )
    assert captured["task"] == "synthesize"
    assert captured["model"] == "openai/gpt-test"
    assert captured["usage"].total_tokens == 15


async def test_cost_callback_exception_is_swallowed() -> None:
    def boom(usage: Usage, model: str, task: str | None) -> None:
        raise RuntimeError("cost service down")

    c = LLMClient(cost_callback=boom)
    with patch("app.llm.client.acompletion", new=AsyncMock(return_value=_fake_response())):
        resp = await c.chat([{"role": "user", "content": "hi"}], model="openai/gpt-test")
    assert resp.content == "hello"


class _Person(BaseModel):
    name: str
    age: int


async def test_structured_parses_valid_json() -> None:
    c = LLMClient()
    with patch(
        "app.llm.client.acompletion",
        new=AsyncMock(return_value=_fake_response('{"name":"Ada","age":36}')),
    ):
        out = await c.structured(
            [{"role": "user", "content": "who"}],
            model="openai/gpt-test",
            schema=_Person,
        )
    assert isinstance(out, _Person)
    assert out.name == "Ada"
    assert out.age == 36


async def test_structured_raises_after_two_bad_attempts() -> None:
    c = LLMClient()
    mock = AsyncMock(return_value=_fake_response("not json"))
    with patch("app.llm.client.acompletion", new=mock):
        with pytest.raises(StructuredOutputError):
            await c.structured(
                [{"role": "user", "content": "who"}],
                model="openai/gpt-test",
                schema=_Person,
            )
    assert mock.await_count == 2


async def test_structured_retries_once_on_validation_error() -> None:
    c = LLMClient()
    mock = AsyncMock(
        side_effect=[
            _fake_response("garbage"),
            _fake_response('{"name":"Ada","age":36}'),
        ]
    )
    with patch("app.llm.client.acompletion", new=mock):
        out = await c.structured(
            [{"role": "user", "content": "who"}],
            model="openai/gpt-test",
            schema=_Person,
        )
    assert out.name == "Ada"
    assert mock.await_count == 2
