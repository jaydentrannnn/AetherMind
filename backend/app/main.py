from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

from app.api.router import router as api_router
from app.config import settings

app = FastAPI(title="AetherMind", version="0.1.0")

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
