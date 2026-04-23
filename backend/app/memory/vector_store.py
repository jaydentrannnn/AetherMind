"""Chroma-backed vector memory store with externally supplied embeddings."""

from __future__ import annotations

try:
    from chromadb import PersistentClient
except ImportError:  # pragma: no cover - used in minimal local test envs
    PersistentClient = None

from app.config import settings
from app.embeddings.client import EmbeddingClient, get_embedding_client


class _InMemoryCollection:
    """Small in-memory collection implementing the subset of Chroma API we use."""

    def __init__(self) -> None:
        """Initialize internal row storage keyed by id."""
        self._rows: dict[str, dict] = {}

    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Insert or replace rows for the provided ids."""
        for idx, item_id in enumerate(ids):
            self._rows[item_id] = {
                "id": item_id,
                "document": documents[idx] if idx < len(documents) else "",
                "embedding": embeddings[idx] if idx < len(embeddings) else [],
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
            }

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
        where: dict | None = None,
    ) -> dict:
        """Return a Chroma-like payload using naive L2 distance ranking."""
        del include
        query = query_embeddings[0] if query_embeddings else []
        rows = list(self._rows.values())
        if where:
            rows = [
                row
                for row in rows
                if all(row["metadata"].get(key) == value for key, value in where.items())
            ]
        ranked = sorted(rows, key=lambda row: _l2_distance(query, row["embedding"]))[:n_results]
        return {
            "ids": [[row["id"] for row in ranked]],
            "documents": [[row["document"] for row in ranked]],
            "metadatas": [[row["metadata"] for row in ranked]],
            "distances": [[_l2_distance(query, row["embedding"]) for row in ranked]],
        }

    def delete(self, *, where: dict) -> None:
        """Delete rows whose metadata fully matches the provided predicate."""
        to_remove = [
            row_id
            for row_id, row in self._rows.items()
            if all(row["metadata"].get(key) == value for key, value in where.items())
        ]
        for row_id in to_remove:
            self._rows.pop(row_id, None)


class _InMemoryClient:
    """Provide get_or_create_collection with in-memory collection instances."""

    def __init__(self) -> None:
        """Initialize collection dictionary for fallback persistence."""
        self._collections: dict[str, _InMemoryCollection] = {}

    def get_or_create_collection(self, *, name: str, embedding_function=None) -> _InMemoryCollection:
        """Return a reusable in-memory collection for a name."""
        del embedding_function
        if name not in self._collections:
            self._collections[name] = _InMemoryCollection()
        return self._collections[name]


def _l2_distance(left: list[float], right: list[float]) -> float:
    """Compute squared L2 distance between two vectors of equal length."""
    if not left or not right or len(left) != len(right):
        return 1.0
    return sum((l - r) ** 2 for l, r in zip(left, right))


class _HashEmbedder:
    """Dependency-free fallback embedder for local tests/dev without ML stacks."""

    dim = 8

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed each text into a deterministic low-dimensional vector."""
        return [await self.embed_one(text) for text in texts]

    async def embed_one(self, text: str) -> list[float]:
        """Convert one text string into a deterministic numeric vector."""
        buckets = [0.0] * self.dim
        for idx, char in enumerate(text):
            buckets[idx % self.dim] += (ord(char) % 31) / 31.0
        return buckets


class VectorStore:
    """Wrap Chroma collections used by memory recall and write paths."""

    def __init__(
        self,
        *,
        embedder: EmbeddingClient | None = None,
        persist_dir: str | None = None,
    ) -> None:
        """Initialize the persistent client and three named collections."""
        if embedder is None:
            try:
                self._embedder = get_embedding_client()
            except Exception:
                self._embedder = _HashEmbedder()
        else:
            self._embedder = embedder
        if PersistentClient is None:
            self._client = _InMemoryClient()
        else:
            self._client = PersistentClient(path=persist_dir or settings.CHROMA_PERSIST_DIR)
        # Embeddings are precomputed through app.embeddings; keep Chroma passive here.
        self._preferences = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_PREFERENCES,
            embedding_function=None,
        )
        self._reports = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_REPORTS,
            embedding_function=None,
        )
        self._scratch = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_SCRATCH,
            embedding_function=None,
        )

    async def add_report_summary(self, report_id: str, topic: str, summary: str) -> None:
        """Embed and upsert one report summary record."""
        vector = await self._embedder.embed_one(summary)
        self._reports.upsert(
            ids=[report_id],
            documents=[summary],
            embeddings=[vector],
            metadatas=[{"topic": topic}],
        )

    async def query_reports(self, topic: str, k: int = 5) -> list[dict]:
        """Return top-k similar report summaries for a topic string."""
        vector = await self._embedder.embed_one(topic)
        result = self._reports.query(
            query_embeddings=[vector],
            n_results=k,
            include=["distances", "documents", "metadatas"],
        )
        return self._format_query(result, id_key="report_id")

    async def add_preference_text(self, user_id: str, key: str, text: str) -> None:
        """Embed and upsert one user preference sentence."""
        vector = await self._embedder.embed_one(text)
        preference_id = f"{user_id}:{key}"
        self._preferences.upsert(
            ids=[preference_id],
            documents=[text],
            embeddings=[vector],
            metadatas=[{"user_id": user_id, "key": key}],
        )

    async def query_preferences(self, topic: str, user_id: str, k: int = 5) -> list[dict]:
        """Return semantic preference matches filtered to one user."""
        vector = await self._embedder.embed_one(topic)
        result = self._preferences.query(
            query_embeddings=[vector],
            n_results=k,
            where={"user_id": user_id},
            include=["distances", "documents", "metadatas"],
        )
        return self._format_query(result, id_key="text")

    def reset_scratch(self, job_id: str) -> None:
        """Delete scratch vectors tied to one job id."""
        self._scratch.delete(where={"job_id": job_id})

    @staticmethod
    def _format_query(raw: dict, *, id_key: str) -> list[dict]:
        """Normalize Chroma query payload into a simple list of dictionaries."""
        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        formatted: list[dict] = []
        for idx, item_id in enumerate(ids):
            metadata = metas[idx] if idx < len(metas) and metas[idx] else {}
            score = 1.0 - float(distances[idx]) if idx < len(distances) else 0.0
            row = dict(metadata)
            row[id_key] = item_id
            if idx < len(docs):
                row.setdefault("text", docs[idx])
                row.setdefault("summary", docs[idx])
            row["score"] = score
            formatted.append(row)
        return formatted
# Chroma collections — memory_service (plan §6).
