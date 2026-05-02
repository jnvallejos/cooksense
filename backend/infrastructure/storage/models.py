"""SQLAlchemy ORM models for persistent storage.

The schema is intentionally simple. Phase 1 holds anonymous user profiles keyed
by `user_id` (a UUID v4 generated client-side and sent in the `X-User-Id`
header). Future phases extend the schema; for now we rely on
`Base.metadata.create_all` rather than Alembic migrations.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cooking_for: Mapped[str] = mapped_column(String(50))
    household_size: Mapped[int] = mapped_column()
    dietary_restrictions: Mapped[list[str]] = mapped_column(JSON, default=list)
    fitness_goal: Mapped[str] = mapped_column(String(50))
    cooking_skill: Mapped[str] = mapped_column(String(50))
    time_budget_minutes: Mapped[int] = mapped_column()
    language: Mapped[str] = mapped_column(String(2), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
