"""Memory preferences and semantic search endpoints."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import db
from app.memory import sqlite_store
from app.models import Preference as PreferenceEntity

router = APIRouter(tags=["memory"])


class PreferencePayload(BaseModel):
    """One frontend memory preference row."""

    key: str
    value: str
    source: str = "user"
    updatedAt: str = ""


class MemoryPreferencesPayload(BaseModel):
    """Frontend-compatible memory preferences response shape."""

    preferences: list[PreferencePayload] = Field(default_factory=list)
    allow_domains: list[str] = Field(default_factory=list)
    deny_domains: list[str] = Field(default_factory=list)


def _source_from_key(key: str) -> str:
    """Infer preference source from key namespace prefix."""
    return "inferred" if key.startswith("inferred:") else "user"


def _serialize_domains(domains: list[str]) -> str:
    """Encode domain list as JSON string for preference storage."""
    return json.dumps(domains)


def _coerce_score(value: object) -> float:
    """Return a numeric score, defaulting to zero when unavailable."""
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


@router.get("/memory/preferences", response_model=MemoryPreferencesPayload)
def get_preferences() -> MemoryPreferencesPayload:
    """Return stored preferences plus allow/deny domain lists."""
    user_id = sqlite_store.ensure_default_user()
    with db.SessionLocal() as session:
        rows = session.scalars(
            select(PreferenceEntity).where(PreferenceEntity.user_id == user_id)
        ).all()
    prefs = [
        PreferencePayload(
            key=row.key,
            value=row.value,
            source=_source_from_key(row.key),
            updatedAt=(row.created_at or datetime.utcnow()).isoformat(),
        )
        for row in rows
        if row.key not in {"allow_domains", "deny_domains"}
    ]
    allow_domains, deny_domains = sqlite_store.get_domain_lists(user_id)
    return MemoryPreferencesPayload(
        preferences=prefs,
        allow_domains=allow_domains,
        deny_domains=deny_domains,
    )


@router.post("/memory/preferences", response_model=MemoryPreferencesPayload)
async def save_preferences(payload: MemoryPreferencesPayload) -> MemoryPreferencesPayload:
    """Upsert preferences and domain lists, then mirror into semantic memory."""
    user_id = sqlite_store.ensure_default_user()
    from app.memory.vector_store import VectorStore

    vector_store = VectorStore()
    for preference in payload.preferences:
        sqlite_store.upsert_preference(user_id, preference.key, preference.value)
        await vector_store.add_preference_text(
            user_id,
            preference.key,
            f"{preference.key}: {preference.value}",
        )
    sqlite_store.upsert_preference(user_id, "allow_domains", _serialize_domains(payload.allow_domains))
    sqlite_store.upsert_preference(user_id, "deny_domains", _serialize_domains(payload.deny_domains))
    return payload


@router.get("/memory/search")
async def search_memory(q: str = Query(..., min_length=1)) -> dict:
    """Run semantic recall over reports and return frontend result rows."""
    from app.memory.vector_store import VectorStore

    vector_store = VectorStore()
    recalled = await vector_store.query_reports(q, k=5)
    if not recalled:
        recalled = sqlite_store.list_reports_for_topic(q, limit=5)
    results = [
        {
            "id": row.get("report_id") or row.get("id") or "",
            "title": row.get("title") or "Untitled report",
            "snippet": row.get("summary") or row.get("text") or "",
            "score": _coerce_score(row.get("score")),
            "date": row.get("created_at") or "",
            "report_id": row.get("report_id"),
        }
        for row in recalled
    ]
    if results is None:
        raise HTTPException(status_code=500, detail="Failed to search memory")
    return {"query": q, "results": results}
