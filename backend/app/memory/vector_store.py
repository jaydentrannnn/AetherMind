"""Chroma-backed vector memory store with externally supplied embeddings."""

from __future__ import annotations

from chromadb import PersistentClient

from app.config import settings
from app.embeddings.client import EmbeddingClient, get_embedding_client


class VectorStore:
    """Wrap Chroma collections used by memory recall and write paths."""

    def __init__(
        self,
        *,
        embedder: EmbeddingClient | None = None,
        persist_dir: str | None = None,
    ) -> None:
        """Initialize the persistent client and three named collections."""
        self._embedder = embedder or get_embedding_client()
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
