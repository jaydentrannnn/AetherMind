"""EmbeddingClient -- embeddings_module (plan §2, Tier 1).

This module is the **only** place in ``backend/app`` allowed to import
``sentence_transformers`` (invariant #2). Consumers call
``get_embedding_client().embed(texts)`` and never touch the underlying provider.

Providers (selected by ``EMBEDDINGS_PROVIDER``):
    * ``sentence-transformers`` -- local, default. Known small families only
      (<1GB). Never load bge-large / instructor-xl here; route to API instead.
    * ``ollama`` -- local via Ollama server (e.g. ``nomic-embed-text``).
    * ``openai`` -- hosted via LiteLLM (e.g. ``text-embedding-3-small``).
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Protocol, runtime_checkable

import httpx

from app.config import settings

# Sentence-transformer model IDs known to fit comfortably under the VRAM cap.
# Anything else must be served via the hosted/openai provider.
_ST_ALLOWLIST: frozenset[str] = frozenset(
    {
        "BAAI/bge-small-en-v1.5",
        "BAAI/bge-small-en",
        "sentence-transformers/all-MiniLM-L6-v2",
        "all-MiniLM-L6-v2",
        "sentence-transformers/all-MiniLM-L12-v2",
        "all-MiniLM-L12-v2",
        "sentence-transformers/paraphrase-MiniLM-L6-v2",
    }
)

_KNOWN_DIMS: dict[str, int] = {
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-small-en": 384,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-MiniLM-L12-v2": 384,
    "all-MiniLM-L12-v2": 384,
}


class EmbeddingsConfigError(RuntimeError):
    """Invalid embeddings configuration."""


@runtime_checkable
class EmbeddingClient(Protocol):
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_one(self, text: str) -> list[float]: ...


class _BaseEmbedder:
    """Shared batching helper."""

    dim: int = 0
    batch_size: int = 64

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i : i + self.batch_size]
            out.extend(await self._embed_batch(chunk))
        return out

    async def embed_one(self, text: str) -> list[float]:
        (vec,) = await self.embed([text])
        return vec

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class SentenceTransformersEmbedder(_BaseEmbedder):
    def __init__(self, model_name: str) -> None:
        if model_name not in _ST_ALLOWLIST:
            raise EmbeddingsConfigError(
                f"sentence-transformers model {model_name!r} is not in the "
                f"<={settings.LOCALVRAM_MAX_GB}GB local allowlist. Allowed: "
                f"{sorted(_ST_ALLOWLIST)}. For larger models use "
                "EMBEDDINGS_PROVIDER=openai."
            )
        # Lazy import keeps the heavy torch dep out of modules that only need
        # the Protocol / hosted providers.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        if model_name in _KNOWN_DIMS:
            self.dim = _KNOWN_DIMS[model_name]
        else:
            # get_embedding_dimension (new) fell back to get_sentence_embedding_dimension (old).
            getter = getattr(self._model, "get_embedding_dimension", None) or getattr(
                self._model, "get_sentence_embedding_dimension", None
            )
            self.dim = int(getter() or 0) if getter else 0

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        def _encode() -> list[list[float]]:
            arr = self._model.encode(
                texts,
                batch_size=len(texts),
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return [row.tolist() for row in arr]

        return await asyncio.to_thread(_encode)


class OllamaEmbedder(_BaseEmbedder):
    def __init__(self, model_name: str, base_url: str, keep_alive: str) -> None:
        self._model_name = model_name
        self._url = f"{base_url.rstrip('/')}/api/embed"
        self._keep_alive = keep_alive
        self.dim = 0
        self._client = httpx.AsyncClient(timeout=60.0)

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": self._model_name,
            "input": texts,
            "keep_alive": self._keep_alive,
        }
        resp = await self._client.post(self._url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings") or []
        if embeddings and not self.dim:
            self.dim = len(embeddings[0])
        return [list(map(float, v)) for v in embeddings]


class OpenAIEmbedder(_BaseEmbedder):
    """Hosted embeddings via LiteLLM (keeps this module decoupled from LLMClient)."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self.dim = 0

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        from litellm import aembedding

        resp = await aembedding(model=self._model_name, input=texts)
        data = resp["data"] if isinstance(resp, dict) else resp.data
        vectors: list[list[float]] = []
        for item in data:
            v = item["embedding"] if isinstance(item, dict) else item.embedding
            vectors.append(list(map(float, v)))
        if vectors and not self.dim:
            self.dim = len(vectors[0])
        return vectors


def _build_client() -> EmbeddingClient:
    provider = settings.EMBEDDINGS_PROVIDER.lower()
    model = settings.EMBEDDINGS_MODEL

    if provider == "sentence-transformers":
        return SentenceTransformersEmbedder(model)
    if provider == "ollama":
        return OllamaEmbedder(
            model_name=model,
            base_url=settings.OLLAMA_BASE_URL,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
    if provider == "openai":
        return OpenAIEmbedder(model)
    raise EmbeddingsConfigError(
        f"Unknown EMBEDDINGS_PROVIDER={provider!r}. "
        "Expected one of: sentence-transformers, ollama, openai."
    )


@lru_cache(maxsize=1)
def get_embedding_client() -> EmbeddingClient:
    """Return the process-wide singleton embedding client.

    Cached so sentence-transformers weights load at most once. Call
    ``get_embedding_client.cache_clear()`` in tests when swapping providers.
    """
    return _build_client()
