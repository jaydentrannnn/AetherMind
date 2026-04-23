"""Research creation and SSE stream endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.jobs import get_job_manager

router = APIRouter(tags=["research"])


class ResearchOptionsRequest(BaseModel):
    """Optional controls used when starting one research job."""

    depth: str | None = None
    tools: dict[str, bool] | None = None
    preferred_domains: list[str] = Field(default_factory=list)


class CreateResearchRequest(BaseModel):
    """Request body for creating a new research job."""

    topic: str
    options: ResearchOptionsRequest | None = None


class CreateResearchResponse(BaseModel):
    """Response payload returned after creating a research job."""

    job_id: str


@router.post("/research", response_model=CreateResearchResponse)
async def create_research(payload: CreateResearchRequest) -> CreateResearchResponse:
    """Create one research job and return its job id."""
    manager = get_job_manager()
    options: dict[str, Any] | None = payload.options.model_dump() if payload.options else None
    job_id = await manager.start(topic=payload.topic, options=options, user_id=None)
    return CreateResearchResponse(job_id=job_id)


@router.get("/research/{job_id}/stream")
async def stream_research(job_id: str) -> StreamingResponse:
    """Stream SSE events for a research job lifecycle."""
    manager = get_job_manager()
    response = StreamingResponse(manager.subscribe(job_id), media_type="text/event-stream")
    # Prevent proxy buffering; SSE must flush events immediately.
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
