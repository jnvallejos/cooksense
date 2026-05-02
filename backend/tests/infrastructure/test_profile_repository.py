"""Tests for the profile repository (CRUD over `UserProfile`)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.storage.models import Base
from infrastructure.storage.profile_repository import ProfileRepository

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def session() -> Session:
    """In-memory SQLite session for isolated repository tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()


def _profile_payload(**overrides) -> dict:
    base = {
        "cooking_for": "self",
        "household_size": 1,
        "dietary_restrictions": [],
        "fitness_goal": "none",
        "cooking_skill": "beginner",
        "time_budget_minutes": 30,
        "language": "en",
    }
    base.update(overrides)
    return base


def test_get_returns_none_for_unknown_user(session):
    repo = ProfileRepository(session)
    assert repo.get(USER_A) is None


def test_upsert_creates_new_profile(session):
    repo = ProfileRepository(session)
    profile = repo.upsert(USER_A, _profile_payload(cooking_skill="intermediate"))

    assert profile.user_id == USER_A
    assert profile.cooking_skill == "intermediate"
    assert profile.created_at is not None
    assert profile.updated_at is not None


def test_get_returns_profile_after_upsert(session):
    repo = ProfileRepository(session)
    repo.upsert(USER_A, _profile_payload())

    fetched = repo.get(USER_A)
    assert fetched is not None
    assert fetched.user_id == USER_A
    assert fetched.cooking_for == "self"


def test_upsert_updates_existing_profile(session):
    repo = ProfileRepository(session)
    repo.upsert(USER_A, _profile_payload(cooking_skill="beginner"))

    updated = repo.upsert(USER_A, _profile_payload(cooking_skill="pro", time_budget_minutes=90))

    assert updated.cooking_skill == "pro"
    assert updated.time_budget_minutes == 90


def test_upsert_updates_updated_at(session):
    repo = ProfileRepository(session)
    created = repo.upsert(USER_A, _profile_payload())
    first_updated_at = created.updated_at

    # Re-upsert with a change.
    refreshed = repo.upsert(USER_A, _profile_payload(time_budget_minutes=60))
    assert refreshed.updated_at >= first_updated_at


def test_upsert_does_not_leak_across_users(session):
    repo = ProfileRepository(session)
    repo.upsert(USER_A, _profile_payload(cooking_skill="beginner"))
    repo.upsert(USER_B, _profile_payload(cooking_skill="pro"))

    assert repo.get(USER_A).cooking_skill == "beginner"
    assert repo.get(USER_B).cooking_skill == "pro"


def test_delete_removes_existing_profile(session):
    repo = ProfileRepository(session)
    repo.upsert(USER_A, _profile_payload())

    deleted = repo.delete(USER_A)

    assert deleted is True
    assert repo.get(USER_A) is None


def test_delete_returns_false_for_unknown(session):
    repo = ProfileRepository(session)
    assert repo.delete(USER_A) is False


def test_dietary_restrictions_round_trip(session):
    repo = ProfileRepository(session)
    repo.upsert(USER_A, _profile_payload(dietary_restrictions=["vegan", "gluten_free"]))

    fetched = repo.get(USER_A)
    assert fetched.dietary_restrictions == ["vegan", "gluten_free"]
