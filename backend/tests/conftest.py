"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.main import create_app
from infrastructure.storage.models import Base
from infrastructure.storage.postgres import get_session


@pytest.fixture
def sqlite_engine():
    """Per-test in-memory SQLite engine. Tables are created on entry."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(sqlite_engine) -> Iterator[Session]:
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def app(sqlite_engine):
    """FastAPI app with `get_session` overridden to use the per-test SQLite engine."""
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)

    def _override_session() -> Iterator[Session]:
        s = factory()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    return app


@pytest.fixture
def client(app) -> TestClient:
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture
def user_id() -> str:
    return "11111111-1111-1111-1111-111111111111"
