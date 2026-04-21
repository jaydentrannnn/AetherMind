"""Tests for ``app.embeddings.client``."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from app.config import settings
from app.embeddings.client import (
    EmbeddingsConfigError,
    OllamaEmbedder,
    OpenAIEmbedder,
    SentenceTransformersEmbedder,
    get_embedding_client,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    get_embedding_client.cache_clear()
    yield
    get_embedding_client.cache_clear()


# ---------- sentence-transformers ----------


def test_sentence_transformers_rejects_unknown_model() -> None:
    with pytest.raises(EmbeddingsConfigError, match="allowlist"):
        SentenceTransformersEmbedder("BAAI/bge-large-en-v1.5")


@pytest.mark.slow
async def test_sentence_transformers_embeds_and_ranks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration: bge-small weights must be available locally."""
    try:
        emb = SentenceTransformersEmbedder("BAAI/bge-small-en-v1.5")
    except Exception as e:
        pytest.skip(f"sentence-transformers model unavailable: {e}")

    assert emb.dim == 384
    vecs = await emb.embed(["cat", "kitten", "car"])
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)

    def cos(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    assert cos(vecs[0], vecs[1]) > cos(vecs[0], vecs[2])


# ---------- ollama ----------


async def test_ollama_embedder_calls_endpoint() -> None:
    emb = OllamaEmbedder(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        keep_alive="-1",
    )
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(
                200, json={"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}
            )
        )
        vecs = await emb.embed(["a", "b"])
    assert vecs == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert emb.dim == 3
    sent = route.calls.last.request
    import json as _json

    body = _json.loads(sent.content)
    assert body["model"] == "nomic-embed-text"
    assert body["input"] == ["a", "b"]
    assert body["keep_alive"] == "-1"


async def test_ollama_embed_one_unwraps_single_vector() -> None:
    emb = OllamaEmbedder(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        keep_alive="-1",
    )
    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": [[0.7, 0.8]]})
        )
        vec = await emb.embed_one("hello")
    assert vec == [0.7, 0.8]


# ---------- openai via litellm ----------


async def test_openai_embedder_uses_litellm_aembedding() -> None:
    emb = OpenAIEmbedder("text-embedding-3-small")
    fake_resp = {
        "data": [
            {"embedding": [0.1, 0.2]},
            {"embedding": [0.3, 0.4]},
        ]
    }
    with patch(
        "litellm.aembedding", new=AsyncMock(return_value=fake_resp)
    ) as mock:
        vecs = await emb.embed(["a", "b"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
    assert emb.dim == 2
    mock.assert_awaited_once()
    assert mock.await_args.kwargs["model"] == "text-embedding-3-small"
    assert mock.await_args.kwargs["input"] == ["a", "b"]


async def test_embed_empty_list_returns_empty() -> None:
    emb = OpenAIEmbedder("text-embedding-3-small")
    with patch("litellm.aembedding", new=AsyncMock()) as mock:
        out = await emb.embed([])
    assert out == []
    mock.assert_not_awaited()


# ---------- factory ----------


def test_get_embedding_client_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMBEDDINGS_PROVIDER", "magic-beans")
    with pytest.raises(EmbeddingsConfigError, match="Unknown EMBEDDINGS_PROVIDER"):
        get_embedding_client()


def test_get_embedding_client_builds_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMBEDDINGS_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "EMBEDDINGS_MODEL", "nomic-embed-text")
    c = get_embedding_client()
    assert isinstance(c, OllamaEmbedder)


def test_get_embedding_client_builds_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMBEDDINGS_PROVIDER", "openai")
    monkeypatch.setattr(settings, "EMBEDDINGS_MODEL", "text-embedding-3-small")
    c = get_embedding_client()
    assert isinstance(c, OpenAIEmbedder)


def test_get_embedding_client_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMBEDDINGS_PROVIDER", "openai")
    monkeypatch.setattr(settings, "EMBEDDINGS_MODEL", "text-embedding-3-small")
    a = get_embedding_client()
    b = get_embedding_client()
    assert a is b
