"""LiteLLM wrapper — llm_gateway (plan §2).

Provider-agnostic async chat client. All model strings are passed in by the
caller; this module never hardcodes them (invariant #1). Consumers should go
through ``app.llm.router`` rather than using this client directly so that task
-> model resolution stays in a single place.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import litellm
from litellm import acompletion
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
    Timeout,
)
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

litellm.drop_params = True


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    raw: Any = None


CostCallback = Callable[[Usage, str, str | None], None]


class LLMError(Exception):
    """Base error for the LLM client."""


class StructuredOutputError(LLMError):
    """Raised when a structured-output call can't be coerced into the schema."""


_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    RateLimitError,
    APIConnectionError,
    Timeout,
)
_NON_RETRYABLE: tuple[type[BaseException], ...] = (
    AuthenticationError,
    BadRequestError,
)


class LLMClient:
    """Async, provider-agnostic chat client backed by LiteLLM.

    LiteLLM already handles retry/backoff via ``num_retries`` and classifies
    errors correctly (auth/bad-request are never retried). We delegate to it
    rather than wrapping our own tenacity loop so behavior matches upstream
    provider semantics across OpenAI, Anthropic, and Ollama.
    """

    def __init__(
        self,
        *,
        num_retries: int = 2,
        default_timeout: float = 60.0,
        cost_callback: CostCallback | None = None,
    ) -> None:
        self._num_retries = num_retries
        self._default_timeout = default_timeout
        self._cost_callback = cost_callback

    def set_cost_callback(self, cb: CostCallback | None) -> None:
        self._cost_callback = cb

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
        timeout: float | None = None,
        metadata: dict[str, Any] | None = None,
        **extra: Any,
    ) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "timeout": timeout or self._default_timeout,
            "num_retries": self._num_retries,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if response_format is not None:
            kwargs["response_format"] = response_format
        if metadata is not None:
            kwargs["metadata"] = metadata
        if model.startswith("ollama/") and settings.OLLAMA_BASE_URL:
            kwargs.setdefault("api_base", settings.OLLAMA_BASE_URL)
            kwargs.setdefault("keep_alive", settings.OLLAMA_KEEP_ALIVE)
        kwargs.update(extra)

        try:
            response = await acompletion(**kwargs)
        except _NON_RETRYABLE:
            raise
        except APIError as e:
            logger.warning("LLM call failed: %s", e)
            raise

        return self._to_chat_response(response, model, metadata)

    async def structured(
        self,
        messages: list[dict[str, Any]],
        model: str,
        schema: type[BaseModel],
        *,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        """Return a validated Pydantic model.

        Strategy: ask the provider for JSON via ``response_format``; if parsing
        or validation fails, retry once with the validation error injected back
        into the prompt. If still invalid, raise ``StructuredOutputError``.
        """
        json_schema = schema.model_json_schema()
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": json_schema, "strict": False},
        }
        messages = list(messages)

        for attempt in range(2):
            resp = await self.chat(
                messages,
                model=model,
                response_format=response_format,
                metadata=metadata,
                **kwargs,
            )
            try:
                return schema.model_validate_json(resp.content)
            except (ValidationError, ValueError) as err:
                if attempt == 1:
                    raise StructuredOutputError(
                        f"Failed to parse {schema.__name__} after 2 attempts: {err}"
                    ) from err
                messages = messages + [
                    {"role": "assistant", "content": resp.content},
                    {
                        "role": "user",
                        "content": (
                            "The previous response did not match the required schema. "
                            f"Validation error: {err}. "
                            "Respond with ONLY valid JSON matching the schema."
                        ),
                    },
                ]
        raise StructuredOutputError("unreachable")

    def _to_chat_response(
        self, response: Any, model: str, metadata: dict[str, Any] | None
    ) -> ChatResponse:
        choice = response.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls: list[dict[str, Any]] = []
        raw_tool_calls = getattr(message, "tool_calls", None) or []
        for tc in raw_tool_calls:
            fn = getattr(tc, "function", None)
            tool_calls.append(
                {
                    "id": getattr(tc, "id", None),
                    "type": getattr(tc, "type", "function"),
                    "name": getattr(fn, "name", None) if fn else None,
                    "arguments": _safe_json_loads(getattr(fn, "arguments", "") if fn else ""),
                }
            )

        raw_usage = getattr(response, "usage", None)
        usage = Usage(
            prompt_tokens=getattr(raw_usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(raw_usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(raw_usage, "total_tokens", 0) or 0,
        )
        try:
            usage.cost_usd = float(litellm.completion_cost(completion_response=response))
        except Exception:
            usage.cost_usd = None

        if self._cost_callback is not None:
            task = (metadata or {}).get("task") if metadata else None
            try:
                self._cost_callback(usage, model, task)
            except Exception:
                logger.exception("cost_callback raised; swallowing")

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=getattr(response, "model", model),
            raw=response,
        )


def _safe_json_loads(s: str) -> Any:
    if not s:
        return {}
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


client = LLMClient()
