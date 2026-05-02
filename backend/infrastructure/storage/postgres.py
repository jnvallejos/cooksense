"""SQLAlchemy engine and session factory.

Uses PostgreSQL in prod (`DATABASE_URL` from env) and SQLite in tests (the
test conftest overrides `_engine` and `SessionLocal` with an in-memory engine).

Phase 1 ships with `Base.metadata.create_all` instead of Alembic. When the
schema changes in a future phase, we will introduce migrations.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.config import settings
from infrastructure.storage.models import Base


def make_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine bound to the given URL (or `settings.database_url`).

    `pool_pre_ping=True` keeps long-lived connections healthy across server-side
    timeouts. SQLite URLs are accepted for tests; the engine arg `connect_args`
    only matters for SQLite, so we keep the call site minimal here and let
    callers customize when needed.
    """
    url = database_url or settings.database_url
    return create_engine(url, pool_pre_ping=True)


_engine: Engine = make_engine()
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables on the active engine. Idempotent; safe to call on startup."""
    Base.metadata.create_all(_engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a per-request session and closes it on exit."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
