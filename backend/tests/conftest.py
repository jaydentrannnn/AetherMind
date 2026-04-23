import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app import db
from app.api.jobs import get_job_manager
from app.config import settings
from app.db import Base
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous TestClient for request-level tests."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    """TestClient fixture with isolated DB and fallback job driver settings."""
    sqlite_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite+pysqlite:///{sqlite_path}")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", testing_session)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(settings, "MODEL_PLANNER", None)
    monkeypatch.setattr(settings, "MODEL_SYNTH", None)
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    get_job_manager.cache_clear()
    with TestClient(app) as c:
        yield c
    get_job_manager.cache_clear()


@pytest.fixture
async def async_ready() -> None:
    """Placeholder fixture confirming the async event loop is available.

    Expand this fixture (e.g. with an in-memory DB override) when
    writing async integration tests.
    """
    yield
