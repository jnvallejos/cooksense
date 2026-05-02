"""Tests for `DailyUsageLimiter` — per-user, per-day call counter + rate limit.

The limiter keeps an atomic counter per (user, date). New day = new row, so
counters reset implicitly with no scheduled job. `check_and_increment` raises
when the per-day limit is reached and otherwise returns the remaining quota.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.storage.daily_usage import DailyUsageLimiter, RateLimitExceeded
from infrastructure.storage.models import Base, UserDailyUsage

USER = "11111111-1111-1111-1111-111111111111"


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


def test_first_call_returns_remaining_minus_one(session):
    limiter = DailyUsageLimiter(session)
    remaining = limiter.check_and_increment(USER, kind="vision", limit=5)
    assert remaining == 4


def test_increments_persist_across_calls(session):
    limiter = DailyUsageLimiter(session)
    limiter.check_and_increment(USER, kind="vision", limit=5)
    limiter.check_and_increment(USER, kind="vision", limit=5)
    remaining = limiter.check_and_increment(USER, kind="vision", limit=5)
    assert remaining == 2


def test_raises_when_over_limit(session):
    limiter = DailyUsageLimiter(session)
    for _ in range(5):
        limiter.check_and_increment(USER, kind="vision", limit=5)

    with pytest.raises(RateLimitExceeded):
        limiter.check_and_increment(USER, kind="vision", limit=5)


def test_qa_and_vision_counters_are_independent(session):
    limiter = DailyUsageLimiter(session)
    limiter.check_and_increment(USER, kind="vision", limit=5)
    remaining_qa = limiter.check_and_increment(USER, kind="qa", limit=10)
    assert remaining_qa == 9

    row = session.execute(select(UserDailyUsage)).scalar_one()
    assert row.vision_calls == 1
    assert row.qa_calls == 1


def test_resets_on_new_day(session):
    """Yesterday's row is untouched; today gets a fresh counter."""
    yesterday = date.today() - timedelta(days=1)
    session.add(UserDailyUsage(user_id=USER, usage_date=yesterday, vision_calls=5, qa_calls=10))
    session.commit()

    limiter = DailyUsageLimiter(session)
    remaining = limiter.check_and_increment(USER, kind="vision", limit=5)

    assert remaining == 4
    rows = (
        session.execute(select(UserDailyUsage).where(UserDailyUsage.user_id == USER))
        .scalars()
        .all()
    )
    assert len(rows) == 2  # yesterday + today
    today_row = next(r for r in rows if r.usage_date == date.today())
    assert today_row.vision_calls == 1
    assert today_row.qa_calls == 0


def test_unknown_kind_raises_value_error(session):
    limiter = DailyUsageLimiter(session)
    with pytest.raises(ValueError):
        limiter.check_and_increment(USER, kind="bogus", limit=5)
