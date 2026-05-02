"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def app():
    """FastAPI app instance for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Synchronous test client. For async tests, use httpx.AsyncClient."""
    return TestClient(app)
