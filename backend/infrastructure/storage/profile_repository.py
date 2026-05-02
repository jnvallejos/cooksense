"""User profile repository.

Encapsulates SQLAlchemy access to `UserProfile`. Routes never touch the
ORM directly: they call methods on the repository, which owns the session
passed in by FastAPI's dependency-injection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from infrastructure.storage.models import UserProfile


class ProfileRepository:
    """CRUD over `UserProfile` keyed by `user_id`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: str) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def upsert(self, user_id: str, fields: dict[str, Any]) -> UserProfile:
        """Create or update a profile by primary key. Returns the persisted row."""
        existing = self.get(user_id)
        if existing is None:
            profile = UserProfile(user_id=user_id, **fields)
            self._session.add(profile)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)
            # SQLite ignores `onupdate` when no column actually changes (e.g. when
            # caller re-sends the exact same fields). Force a refresh of
            # updated_at so callers can rely on it bumping.
            existing.updated_at = datetime.now(UTC)
            profile = existing

        self._session.commit()
        self._session.refresh(profile)
        return profile

    def delete(self, user_id: str) -> bool:
        """Test helper. Not exposed via API. Returns True if a row was removed."""
        existing = self.get(user_id)
        if existing is None:
            return False
        self._session.delete(existing)
        self._session.commit()
        return True
