"""Bilingual language tests for `POST /api/meal-plan/{plan_id}/shopping`.

The response language is the language of the saved plan, which itself is the
profile's language at plan creation time. The shopping endpoint must surface
that language verbatim.
"""

from __future__ import annotations

import pytest

from api.deps import get_recipe_repository


class _FakeRepo:
    def __init__(self) -> None:
        self.recipes = [
            {
                "id": f"r{i:03d}",
                "title": f"Recipe {i}",
                "title_es": f"Receta {i}",
                "ingredients": ["x"],
                "estimated_time_minutes": 5,
            }
            for i in range(15)
        ]

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        return list(self.recipes[:limit])


@pytest.fixture(autouse=True)
def _high_rate_limit(monkeypatch):
    from infrastructure import config as config_module

    monkeypatch.setattr(config_module.settings, "rate_limit_meal_plan_per_day", 100)


@pytest.fixture
def fake_repo(app) -> _FakeRepo:
    repo = _FakeRepo()
    app.dependency_overrides[get_recipe_repository] = lambda: repo
    return repo


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id, "Content-Type": "application/json"}


def _create_plan(client, headers) -> str:
    response = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta"]},
    )
    return response.json()["plan_id"]


def test_default_language_is_en_when_no_profile(client, headers, fake_repo):
    plan_id = _create_plan(client, headers)
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)
    assert response.json()["language"] == "en"


def test_es_profile_yields_es_response(client, headers, fake_repo):
    profile = {
        "cooking_for": "self",
        "household_size": 1,
        "dietary_restrictions": [],
        "fitness_goal": "none",
        "cooking_skill": "intermediate",
        "time_budget_minutes": 30,
        "language": "es",
    }
    client.post("/api/profile", json=profile, headers=headers)

    plan_id = _create_plan(client, headers)
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)
    assert response.json()["language"] == "es"


def test_language_locked_to_plan_value(client, headers, fake_repo):
    """Even if the profile language changes after plan creation, the saved
    plan's language continues to drive the shopping list."""
    profile = {
        "cooking_for": "self",
        "household_size": 1,
        "dietary_restrictions": [],
        "fitness_goal": "none",
        "cooking_skill": "intermediate",
        "time_budget_minutes": 30,
        "language": "es",
    }
    client.post("/api/profile", json=profile, headers=headers)
    plan_id = _create_plan(client, headers)

    # Flip language after the plan is persisted
    profile_en = dict(profile)
    profile_en["language"] = "en"
    client.post("/api/profile", json=profile_en, headers=headers)

    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)
    assert response.json()["language"] == "es"
