"""Validation tests for profile request/response models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.models.profile import ProfileRequest, ProfileResponse


def _request(**overrides) -> dict:
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


def test_profile_request_accepts_minimum_fields():
    profile = ProfileRequest(**_request())
    assert profile.cooking_for == "self"
    assert profile.language == "en"


def test_profile_request_default_language_is_english():
    payload = _request()
    payload.pop("language")
    assert ProfileRequest(**payload).language == "en"


def test_profile_request_rejects_invalid_cooking_for():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(cooking_for="enterprise"))


def test_profile_request_rejects_invalid_skill():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(cooking_skill="hacker"))


def test_profile_request_rejects_invalid_language():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(language="pt"))


def test_profile_request_household_size_lower_bound():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(household_size=0))


def test_profile_request_household_size_upper_bound():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(household_size=21))


def test_profile_request_time_budget_lower_bound():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(time_budget_minutes=10))


def test_profile_request_time_budget_upper_bound():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(time_budget_minutes=181))


def test_profile_request_rejects_invalid_fitness_goal():
    with pytest.raises(ValidationError):
        ProfileRequest(**_request(fitness_goal="bulk_max"))


def test_profile_response_round_trips_timestamps():
    now = datetime.now(UTC)
    response = ProfileResponse(
        user_id="11111111-1111-1111-1111-111111111111",
        cooking_for="self",
        household_size=1,
        dietary_restrictions=["vegan"],
        fitness_goal="none",
        cooking_skill="beginner",
        time_budget_minutes=30,
        language="en",
        created_at=now,
        updated_at=now,
    )
    assert response.dietary_restrictions == ["vegan"]
    assert response.created_at == now
