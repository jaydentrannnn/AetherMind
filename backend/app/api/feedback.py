"""Feedback endpoint for report accept/reject comments."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app import db
from app.memory import get_memory_service
from app.models import Feedback as FeedbackEntity
from app.models import Report as ReportEntity

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    """Payload for submitting report feedback."""

    report_id: str
    accepted: bool
    user_comment: str | None = None


class FeedbackResponse(BaseModel):
    """Response payload after persisting feedback."""

    id: str
    created_at: str


async def _async_memory_feedback_write(feedback_text: str) -> None:
    """Run memory preference extraction without blocking the request thread."""
    try:
        await get_memory_service().write({"feedback": feedback_text})
    except Exception:
        # Optional runtime dependency failures should not break feedback persistence.
        return


@router.post("/feedback", response_model=FeedbackResponse)
def post_feedback(payload: FeedbackRequest, background_tasks: BackgroundTasks) -> FeedbackResponse:
    """Persist feedback and schedule an async memory extraction task."""
    with db.SessionLocal() as session:
        report = session.get(ReportEntity, payload.report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        row = FeedbackEntity(
            report_id=payload.report_id,
            accepted_bool=payload.accepted,
            user_comment=payload.user_comment,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

    if payload.user_comment:
        # BackgroundTasks can run coroutine callables in FastAPI/Starlette.
        background_tasks.add_task(_async_memory_feedback_write, payload.user_comment)

    created = row.created_at or datetime.now(timezone.utc)
    return FeedbackResponse(id=row.id, created_at=created.isoformat())
