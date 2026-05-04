"""Persistence integration tests for `POST /api/meal-plan/generate`.

The endpoint is expected to persist each generated plan via
`MealPlanRepository.save` so the shopping list endpoint can later derive
items from `plan.pantry_ingredients` and `plan.recipes`.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from api.deps import get_recipe_repository
from infrastructure.storage.meal_plan_repository import MealPlanRepository
from infrastructure.storage.models import MealPlan, MealPlanRecipe


class _FakeRepo:
    def __init__(self) -> None:
        self.recipes = [
            {
                "id": f"r{i:03d}",
                "title": f"Recipe {i}",
                "title_es": f"Receta {i}",
                "ingredients": [f"ing{i}-1", f"ing{i}-2"],
                "estimated_time_minutes": 10 + i,
            }
            for i in range(15)
        ]

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        return list(self.recipes[:limit])


@pytest.fixture
def fake_repo(app) -> _FakeRepo:
    repo = _FakeRepo()
    app.dependency_overrides[get_recipe_repository] = lambda: repo
    return repo


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id, "Content-Type": "application/json"}


@pytest.fixture
def payload() -> dict:
    return {
        "ingredients": ["pasta", "tomato", "onion", "chicken", "rice"],
        "days": 3,
        "meals_per_day": ["breakfast", "lunch", "dinner"],
    }


def test_plan_is_persisted_with_pantry_and_recipes(client, headers, payload, fake_repo, session):
    response = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    assert response.status_code == 201
    plan_id = response.json()["plan_id"]

    plan = session.execute(select(MealPlan).where(MealPlan.plan_id == plan_id)).scalar_one()
    assert plan.user_id == headers["X-User-Id"]
    assert plan.pantry_ingredients == [
        "pasta",
        "tomato",
        "onion",
        "chicken",
        "rice",
    ]
    assert plan.days == 3
    assert plan.meals_per_day == ["breakfast", "lunch", "dinner"]
    assert plan.language == "en"

    recipes = session.execute(select(MealPlanRecipe)).scalars().all()
    assert len(recipes) == 9


def test_plan_id_returned_in_response_matches_persisted_row(
    client, headers, payload, fake_repo, session
):
    response = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    plan_id = response.json()["plan_id"]
    plan = MealPlanRepository(session).get_by_id(plan_id)
    assert plan is not None
    assert plan.plan_id == plan_id


def test_two_calls_persist_two_distinct_plans(client, headers, payload, fake_repo, session):
    first = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={**payload, "ingredients": payload["ingredients"] + ["a"]},
    )
    second = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={**payload, "ingredients": payload["ingredients"] + ["b"]},
    )

    assert first.json()["plan_id"] != second.json()["plan_id"]
    plans = session.execute(select(MealPlan)).scalars().all()
    assert len(plans) == 2
