import os
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import router as api_router
from app.config import settings
from app.observability import get_tracer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure structlog, wire LiteLLM → Langfuse, and flush on shutdown."""
    is_prod = os.getenv("ENVIRONMENT", "development") == "production"
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(__import__("logging"), log_level_name, 20)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if is_prod else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    try:
        import litellm  # type: ignore[import-not-found]
        # LiteLLM's Langfuse integration expects `langfuse.version.__version__`.
        # Some Langfuse SDK builds import fine but don't expose that module; in that
        # case, we must avoid enabling the callback or jobs can crash mid-run.
        callbacks = list(getattr(litellm, "success_callback", []) or [])
        if "langfuse" in callbacks:
            try:
                import langfuse  # type: ignore[import-not-found]

                _ = langfuse.version.__version__  # type: ignore[attr-defined]
            except Exception:
                callbacks = [c for c in callbacks if c != "langfuse"]
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                import langfuse  # type: ignore[import-not-found]

                _ = langfuse.version.__version__  # type: ignore[attr-defined]
                callbacks = [c for c in callbacks if c != "langfuse"] + ["langfuse"]
            except Exception:
                callbacks = [c for c in callbacks if c != "langfuse"]
        else:
            callbacks = [c for c in callbacks if c != "langfuse"]
        litellm.success_callback = callbacks
    except Exception:
        pass
    yield
    get_tracer().flush()


app = FastAPI(title="AetherMind", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request id to each response and request state."""

    async def dispatch(self, request, call_next):  # type: ignore[override]
        """Generate request id, expose it in state, and set response header."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


app.add_middleware(RequestIdMiddleware)
app.include_router(api_router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
