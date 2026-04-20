import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous TestClient for request-level tests."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_ready() -> None:
    """Placeholder fixture confirming the async event loop is available.

    Expand this fixture (e.g. with an in-memory DB override) when
    writing async integration tests.
    """
    yield
