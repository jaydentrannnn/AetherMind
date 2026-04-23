"""Memory service exports for planner and writer nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.memory.service import MemoryService

__all__ = ["MemoryService", "get_memory_service"]


def get_memory_service():
    """Return the process-wide memory service with a lazy import."""
    from app.memory.service import get_memory_service as _get_memory_service

    return _get_memory_service()
