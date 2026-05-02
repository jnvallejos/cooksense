"""Per-user, per-day call counter with rate-limit enforcement.

`DailyUsageLimiter.check_and_increment` is the single point that endpoints
call before invoking a paid LLM. It:

1. Fetches (or creates) today's row for the user.
2. Reads the current counter for the requested kind (`vision` or `qa`).
3. Raises `RateLimitExceeded` when the counter has reached `limit`.
4. Otherwise increments the counter and returns the remaining quota.

Daily reset is implicit: a new (user_id, date) row appears for each new day,
so yesterday's counters never need to be cleared.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from sqlalchemy.orm import Session

from infrastructure.storage.models import UserDailyUsage

UsageKind = Literal["vision", "qa"]
_KIND_TO_COLUMN: dict[str, str] = {"vision": "vision_calls", "qa": "qa_calls"}


class RateLimitExceeded(Exception):
    """Raised when the per-user daily limit for a given kind is reached."""


class DailyUsageLimiter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def check_and_increment(self, user_id: str, kind: UsageKind, limit: int) -> int:
        """Atomic check-and-increment. Returns remaining quota for the day.

        Raises:
            RateLimitExceeded: when current_count >= limit before incrementing.
            ValueError: when `kind` is not one of `vision` or `qa`.
        """
        column = _KIND_TO_COLUMN.get(kind)
        if column is None:
            raise ValueError(f"unknown usage kind: {kind!r}")

        today = date.today()
        row = self._session.get(UserDailyUsage, (user_id, today))
        if row is None:
            row = UserDailyUsage(user_id=user_id, usage_date=today)
            self._session.add(row)
            self._session.flush()

        current = getattr(row, column)
        if current >= limit:
            raise RateLimitExceeded(f"user {user_id} reached daily {kind} limit ({limit})")

        setattr(row, column, current + 1)
        self._session.commit()
        return limit - (current + 1)
