"""Aggregate FastAPI API routers for the public application surface."""

from fastapi import APIRouter

from app.api.feedback import router as feedback_router
from app.api.memory import router as memory_router
from app.api.reports import router as reports_router
from app.api.research import router as research_router

router = APIRouter()
router.include_router(research_router)
router.include_router(reports_router)
router.include_router(feedback_router)
router.include_router(memory_router)
