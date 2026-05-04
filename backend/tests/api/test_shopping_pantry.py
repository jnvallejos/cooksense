"""Pantry subtraction tests for `POST /api/meal-plan/{plan_id}/shopping`.

Per spec section 4.2 step 6: pantry subtraction is case-insensitive substring
match. Ingredients already in `plan.pantry_ingredients` should not appear in
the shopping list.
"""

from __future__ import annotations

import pytest

from api.deps import get_meal_planner, get_recipe_repository


class _StaticRepo:
    """Always returns the same recipe carrying a fixed ingredient set."""

    def __init__(self, ingredients: list[str]) -> None:
        self._ingredients = ingredients

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        return [
            {
                "id": f"r{i:03d}",
                "title": f"Recipe {i}",
                "title_es": f"Receta {i}",
                "ingredients": list(self._ingredients),
                "estimated_time_minutes": 5,
            }
            for i in range(limit)
        ]


class _DeterministicPlanner:
    """Picks the first candidate for every slot so the recipes are predictable."""

    def plan(self, ingredients, profile, candidates, days=3, meals_per_day=None, max_tokens=4096):
        meals_per_day = meals_per_day or ["breakfast", "lunch", "dinner"]
        days_data = []
        idx = 0
        for day_number in range(1, days + 1):
            meals = []
            for slot in meals_per_day:
                recipe = candidates[idx % len(candidates)]
                meals.append(
                    {
                        "slot": slot,
                        "recipe": {
                            "id": recipe["id"],
                            "title": recipe.get("title", ""),
                            "title_es": recipe.get("title_es"),
                            "estimated_time_minutes": recipe.get("estimated_time_minutes", 5),
                            "match_percentage": 0.5,
                            "ingredients_summary": list(recipe.get("ingredients") or [])[:3],
                            "personalized_note": "n",
                            "ingredients": list(recipe.get("ingredients") or []),
                        },
                    }
                )
                idx += 1
            days_data.append({"day_number": day_number, "meals": meals})
        return {
            "days": days_data,
            "ingredient_reuse_score": 0.5,
            "variety_score": 0.5,
            "macro_alignment_score": 0.5,
        }


@pytest.fixture(autouse=True)
def _high_rate_limit(monkeypatch):
    from infrastructure import config as config_module

    monkeypatch.setattr(config_module.settings, "rate_limit_meal_plan_per_day", 100)


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id, "Content-Type": "application/json"}


def _setup(app, ingredients):
    repo = _StaticRepo(ingredients=ingredients)
    app.dependency_overrides[get_recipe_repository] = lambda: repo
    app.dependency_overrides[get_meal_planner] = lambda: _DeterministicPlanner()
    return repo


def test_pantry_items_are_excluded_from_shopping_list(client, app, headers):
    _setup(app, ["pasta", "tomato", "salt"])
    create = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta", "tomato"]},
    )
    plan_id = create.json()["plan_id"]
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)

    assert response.status_code == 200
    items = {i["ingredient"] for i in response.json()["items"]}
    assert "pasta" not in items
    assert "tomato" not in items
    assert "salt" in items


def test_pantry_subtraction_is_case_insensitive(client, app, headers):
    _setup(app, ["TOMATO", "BEEF", "rice"])
    create = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["Tomato", "Beef"]},
    )
    plan_id = create.json()["plan_id"]
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)

    items = {i["ingredient"].lower() for i in response.json()["items"]}
    assert "tomato" not in items
    assert "beef" not in items
    assert "rice" in items


def test_pantry_subtraction_matches_substring(client, app, headers):
    """When the recipe carries 'fresh tomato', a pantry of 'tomato' must remove it."""
    _setup(app, ["fresh tomato", "olive oil"])
    create = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["tomato"]},
    )
    plan_id = create.json()["plan_id"]
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)

    items = {i["ingredient"] for i in response.json()["items"]}
    assert "fresh tomato" not in items
    assert "olive oil" in items


def test_total_items_reflects_subtraction(client, app, headers):
    _setup(app, ["pasta", "tomato", "salt", "onion"])
    create = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta", "tomato"]},
    )
    plan_id = create.json()["plan_id"]
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)

    body = response.json()
    assert body["total_items"] == len(body["items"])
    assert body["total_items"] == 2
