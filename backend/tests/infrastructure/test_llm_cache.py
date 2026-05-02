"""Tests for `LLMCache` — DB-backed cache for LLM responses.

The cache is keyed by deterministic SHA-256 hashes built from `kind` plus
opaque components. Entries carry a TTL; expired rows are deleted lazily on
read so we never need a background sweeper.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.storage.llm_cache import LLMCache
from infrastructure.storage.models import Base, LLMCacheEntry


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()


def test_get_returns_none_when_key_absent(session):
    cache = LLMCache(session)
    assert cache.get("missing") is None


def test_set_and_get_round_trip(session):
    cache = LLMCache(session)
    cache.set("k1", kind="vision", payload={"hello": "world"}, ttl_seconds=3600)

    assert cache.get("k1") == {"hello": "world"}


def test_set_overwrites_existing_entry(session):
    cache = LLMCache(session)
    cache.set("k1", kind="vision", payload={"first": True}, ttl_seconds=3600)
    cache.set("k1", kind="vision", payload={"second": True}, ttl_seconds=3600)

    assert cache.get("k1") == {"second": True}


def test_get_returns_none_after_ttl_expires(session):
    cache = LLMCache(session)
    cache.set("k1", kind="vision", payload={"x": 1}, ttl_seconds=3600)

    # Force expiry by rewriting `expires_at` into the past.
    entry = session.execute(select(LLMCacheEntry).where(LLMCacheEntry.cache_key == "k1")).scalar_one()
    entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    assert cache.get("k1") is None


def test_get_lazy_deletes_expired_row(session):
    cache = LLMCache(session)
    cache.set("k1", kind="vision", payload={"x": 1}, ttl_seconds=3600)
    entry = session.execute(select(LLMCacheEntry).where(LLMCacheEntry.cache_key == "k1")).scalar_one()
    entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    cache.get("k1")  # triggers eviction

    rows = session.execute(select(LLMCacheEntry)).scalars().all()
    assert rows == []


def test_get_increments_access_count(session):
    cache = LLMCache(session)
    cache.set("k1", kind="vision", payload={"x": 1}, ttl_seconds=3600)

    cache.get("k1")
    cache.get("k1")

    entry = session.execute(select(LLMCacheEntry).where(LLMCacheEntry.cache_key == "k1")).scalar_one()
    assert entry.access_count == 2


def test_make_key_is_deterministic(session):
    cache = LLMCache(session)
    a = cache.make_key("vision", "image-hash-abc")
    b = cache.make_key("vision", "image-hash-abc")
    assert a == b


def test_make_key_differs_for_different_components(session):
    cache = LLMCache(session)
    a = cache.make_key("vision", "image-hash-abc")
    b = cache.make_key("vision", "image-hash-xyz")
    assert a != b


def test_make_key_differs_for_different_kinds(session):
    cache = LLMCache(session)
    a = cache.make_key("vision", "shared-component")
    b = cache.make_key("qa", "shared-component")
    assert a != b
