"""DB-backed LLM response cache.

`LLMCache` is the single insertion/lookup point for any cached Anthropic call
(vision, personalization, QA). Keys are deterministic SHA-256 hashes built from
a `kind` discriminator plus opaque components, so independent call sites can
build the same key without coordination. TTLs drive lazy eviction: rows past
their `expires_at` are deleted on read so we never need a background sweeper.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from infrastructure.storage.models import LLMCacheEntry


class LLMCache:
    """Repository over `LLMCacheEntry`. Owns nothing but a session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str) -> dict | None:
        """Return the cached payload or `None`. Expired rows are deleted in place."""
        entry = self._session.get(LLMCacheEntry, key)
        if entry is None:
            return None

        now = datetime.now(UTC)
        expires_at = entry.expires_at
        # SQLite returns naive datetimes; treat them as UTC for comparison.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at <= now:
            self._session.delete(entry)
            self._session.commit()
            return None

        entry.access_count += 1
        self._session.commit()
        return entry.payload

    def set(self, key: str, kind: str, payload: dict, ttl_seconds: int) -> None:
        """Insert or overwrite a cache entry."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)

        existing = self._session.get(LLMCacheEntry, key)
        if existing is None:
            self._session.add(
                LLMCacheEntry(
                    cache_key=key,
                    kind=kind,
                    payload=payload,
                    created_at=now,
                    expires_at=expires_at,
                    access_count=0,
                )
            )
        else:
            existing.kind = kind
            existing.payload = payload
            existing.created_at = now
            existing.expires_at = expires_at
            existing.access_count = 0
        self._session.commit()

    def make_key(self, kind: str, *components: str) -> str:
        """Deterministic SHA-256 hash over `kind` + components.

        Joining with a separator that cannot appear in either side keeps the
        encoding injective: distinct (kind, components) pairs always map to
        distinct keys.
        """
        joined = "\x1f".join((kind, *components))
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()
