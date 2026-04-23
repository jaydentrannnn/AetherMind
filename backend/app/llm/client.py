"""LiteLLM wrapper — llm_gateway (plan §2).

Provider-agnostic async chat client. All model strings are passed in by the
caller; this module never hardcodes them (invariant #1). Consumers should go
through ``app.llm.router`` rather than using this client directly so that task
-> model resolution stays in a single place.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# region debug log helper
_DEBUG_LOG_PATH = Path(__file__).resolve().parents[3] / "debug-be98c3.log"


def _dbg(hid: str, loc: str, msg: str, data: dict[str, Any]) -> None:
    """Append one NDJSON line to the debug log; swallow all errors."""
    try:
        payload = {
            "sessionId": "be98c3",
            "hypothesisId": hid,
            "location": loc,
            "message": msg,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass
# endregion

try:
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
except ImportError:  # pragma: no cover - exercised in minimal local environments
    litellm = None

    class APIError(Exception):
        """Fallback APIError when litellm is unavailable."""

    class APIConnectionError(APIError):
        """Fallback APIConnectionError when litellm is unavailable."""

    class AuthenticationError(APIError):
        """Fallback AuthenticationError when litellm is unavailable."""

    class BadRequestError(APIError):
        """Fallback BadRequestError when litellm is unavailable."""

    class RateLimitError(APIError):
        """Fallback RateLimitError when litellm is unavailable."""

    class Timeout(APIError):
        """Fallback Timeout when litellm is unavailable."""

    async def acompletion(**kwargs: Any) -> Any:
        """Raise an explicit error for missing litellm runtime dependency."""
        del kwargs
        raise APIError("litellm is not installed in this environment")
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

if litellm is not None:
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
        default_timeout: float = 540.0,
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

        # region agent log
        task_tag = (metadata or {}).get("task") if metadata else None
        prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)
        has_rf = response_format is not None
        _dbg(
            "H1",
            "client.py:chat:enter",
            "llm_call_start",
            {
                "task": task_tag,
                "model": model,
                "timeout": kwargs["timeout"],
                "num_retries": kwargs["num_retries"],
                "msg_count": len(messages),
                "prompt_chars": prompt_chars,
                "has_response_format": has_rf,
                "max_tokens": max_tokens,
            },
        )
        t0 = time.monotonic()
        # endregion

        try:
            response = await acompletion(**kwargs)
        except _NON_RETRYABLE as e:
            # region agent log
            _dbg(
                "H1",
                "client.py:chat:non_retryable",
                "llm_call_non_retryable_error",
                {
                    "task": task_tag,
                    "model": model,
                    "duration_s": round(time.monotonic() - t0, 2),
                    "exc_type": type(e).__name__,
                    "exc_msg": str(e)[:400],
                },
            )
            # endregion
            raise
        except APIError as e:
            # region agent log
            _dbg(
                "H1",
                "client.py:chat:api_error",
                "llm_call_api_error",
                {
                    "task": task_tag,
                    "model": model,
                    "duration_s": round(time.monotonic() - t0, 2),
                    "exc_type": type(e).__name__,
                    "exc_msg": str(e)[:400],
                },
            )
            # endregion
            logger.warning("LLM call failed: %s", e)
            raise

        # region agent log
        try:
            content_len = len((response.choices[0].message.content or ""))
        except Exception:
            content_len = -1
        _dbg(
            "H1",
            "client.py:chat:ok",
            "llm_call_ok",
            {
                "task": task_tag,
                "model": model,
                "duration_s": round(time.monotonic() - t0, 2),
                "content_chars": content_len,
            },
        )
        # endregion
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

        For hosted providers: use ``response_format=json_schema``.
        For Ollama: skip response_format (incompatible with thinking models like
        Qwen3) and inject the schema + /no_think into the system prompt instead.
        """
        json_schema = schema.model_json_schema()
        messages = list(messages)

        if model.startswith("ollama/"):
            return await self._structured_ollama(
                messages, model, schema, json_schema, metadata=metadata, **kwargs
            )

        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": json_schema, "strict": False},
        }
        for attempt in range(2):
            resp = await self.chat(
                messages,
                model=model,
                response_format=response_format,
                metadata=metadata,
                **kwargs,
            )
            content = _strip_think_tags(resp.content)
            try:
                return schema.model_validate_json(content)
            except (ValidationError, ValueError) as err:
                if attempt == 1:
                    raise StructuredOutputError(
                        f"Failed to parse {schema.__name__} after 2 attempts: {err}"
                    ) from err
                messages = messages + [
                    {"role": "assistant", "content": content},
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

    async def _structured_ollama(
        self,
        messages: list[dict[str, Any]],
        model: str,
        schema: type[BaseModel],
        json_schema: dict[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        """Structured output for Ollama models via prompt injection.

        Ollama's Qwen3 family uses thinking mode by default; response_format
        causes empty content. Instead: inject /no_think + schema into a system
        message and use format='json' (Ollama's basic JSON mode).
        """
        fields = _schema_to_plain(json_schema)
        system_content = (
            "/no_think\n"
            "Respond with ONLY a valid JSON object. No explanation, no markdown, no code fences.\n"
            f"Required fields: {fields}"
        )
        if messages and messages[0].get("role") == "system":
            patched = [{**messages[0], "content": system_content + "\n\n" + messages[0]["content"]}]
            messages = patched + messages[1:]
        else:
            messages = [{"role": "system", "content": system_content}] + messages

        _ollama_timeout = kwargs.pop("timeout", 180.0)
        for attempt in range(2):
            # region agent log
            _dbg(
                "H3",
                "client.py:_structured_ollama:attempt",
                "ollama_structured_attempt",
                {
                    "model": model,
                    "schema": schema.__name__,
                    "attempt": attempt,
                    "timeout": _ollama_timeout,
                    "sys_prompt_chars": len(system_content),
                    "has_no_think_tag": "/no_think" in system_content,
                },
            )
            # endregion
            resp = await self.chat(
                messages,
                model=model,
                timeout=_ollama_timeout,
                metadata=metadata,
                **kwargs,
            )
            content = _strip_think_tags(resp.content)
            # region agent log
            _dbg(
                "H3",
                "client.py:_structured_ollama:post_chat",
                "ollama_structured_content",
                {
                    "model": model,
                    "attempt": attempt,
                    "raw_chars": len(resp.content or ""),
                    "stripped_chars": len(content),
                    "starts_with": (content[:60] if content else ""),
                },
            )
            # endregion
            # Extract first JSON object/array if the model wrapped it in extra text
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                content = m.group()
            try:
                return schema.model_validate_json(content)
            except (ValidationError, ValueError) as err:
                if attempt == 1:
                    raise StructuredOutputError(
                        f"Failed to parse {schema.__name__} after 2 attempts: {err}"
                    ) from err
                messages = messages + [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": (
                            "Invalid JSON. Validation error: "
                            f"{err}. Return ONLY valid JSON matching the schema."
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


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _schema_to_plain(json_schema: dict[str, Any]) -> str:
    """Convert a JSON schema to a compact field list string for prompt injection.

    Avoids dumping the raw schema (hundreds of tokens) which confuses small
    local models and causes Ollama to hang before inference starts.
    """
    props = json_schema.get("properties", {})
    defs = json_schema.get("$defs", {})
    parts: list[str] = []
    for name, spec in props.items():
        # Resolve $ref
        if "$ref" in spec:
            ref_name = spec["$ref"].split("/")[-1]
            spec = defs.get(ref_name, spec)
        # anyOf: pick first non-null type
        if "anyOf" in spec:
            non_null = [s for s in spec["anyOf"] if s.get("type") != "null"]
            spec = non_null[0] if non_null else spec
        t = spec.get("type", "any")
        if t == "object":
            sub = ", ".join(f"{k}({v.get('type','any')})" for k, v in spec.get("properties", {}).items())
            parts.append(f"{name}(object{{{sub}}} or null)")
        elif t == "array":
            item_type = spec.get("items", {}).get("type", "any")
            parts.append(f"{name}(array of {item_type})")
        else:
            parts.append(f"{name}({t})")
    return ", ".join(parts)


def _strip_think_tags(text: str) -> str:
    """Strip Qwen3/DeepSeek chain-of-thought blocks so only JSON remains."""
    return _THINK_RE.sub("", text).strip()


def _safe_json_loads(s: str) -> Any:
    if not s:
        return {}
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


client = LLMClient()
