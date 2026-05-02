"""SQLAlchemy ORM models for persistent storage.

The schema is intentionally simple. Phase 1 holds anonymous user profiles keyed
by `user_id` (a UUID v4 generated client-side and sent in the `X-User-Id`
header). Phase 2 adds an LLM response cache and a per-user daily usage table
for rate limiting. Future phases extend the schema; for now we rely on
`Base.metadata.create_all` rather than Alembic migrations.
"""

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, String
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


class LLMCacheEntry(Base):
    """Cache entry for any LLM-derived response (vision, personalization, QA).

    `cache_key` is a deterministic SHA-256 hash built by `LLMCache.make_key`.
    `kind` lets callers query/maintain a single class of entries (`vision`,
    `personalize`, `qa`). `expires_at` drives lazy eviction — entries past
    their TTL are deleted on read.
    """

    __tablename__ = "llm_cache"

    cache_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    access_count: Mapped[int] = mapped_column(default=0)


class UserDailyUsage(Base):
    """Per-user, per-day call counters for rate limiting.

    The composite primary key (`user_id`, `usage_date`) means a new day
    automatically starts a fresh counter row — yesterday's row is read-only and
    untouched. Atomic increment is the responsibility of `DailyUsageLimiter`.
    """

    __tablename__ = "user_daily_usage"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    vision_calls: Mapped[int] = mapped_column(default=0)
    qa_calls: Mapped[int] = mapped_column(default=0)
