"""Cache tests for `POST /api/meal-plan/generate`.

The endpoint must:
- short-circuit on cache hit (no planner call, response carries `from_cache=True`)
- key cache entries by `(sorted_canonical_ingredients, profile_signature)` so
  reordered or differently-cased pantry inputs hit the same cached plan
- bucket distinct ingredients sets to distinct cache entries
- treat the planner as the source of truth on cache miss (writes the entry)
"""

from __future__ import annotations

import pytest

from api.deps import get_meal_planner, get_recipe_repository


class _FakeRepo:
    def __init__(self) -> None:
        self.recipes = [
            {
                "id": f"r{i:03d}",
                "title": f"Recipe {i}",
                "title_es": f"Receta {i}",
                "ingredients": ["ing"],
                "estimated_time_minutes": 10,
            }
            for i in range(15)
        ]

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        return list(self.recipes[:limit])


class _CountingPlanner:
    def __init__(self) -> None:
        self.calls = 0

    def plan(
        self,
        ingredients: list[str],
        profile: dict,
        candidates: list[dict],
        days: int = 3,
        meals_per_day: list[str] | None = None,
        max_tokens: int = 4096,
    ) -> dict:
        self.calls += 1
        meals_per_day = meals_per_day or ["breakfast", "lunch", "dinner"]
        days_data = []
        for day_number in range(1, days + 1):
            meals = []
            for slot in meals_per_day:
                meals.append(
                    {
                        "slot": slot,
                        "recipe": {
                            "id": f"call{self.calls}-d{day_number}-{slot}",
                            "title": "T",
                            "title_es": "T",
                            "estimated_time_minutes": 5,
                            "match_percentage": 0.5,
                            "ingredients_summary": ["x"],
                            "personalized_note": "n",
                        },
                    }
                )
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
def fake_repo(app) -> _FakeRepo:
    repo = _FakeRepo()
    app.dependency_overrides[get_recipe_repository] = lambda: repo
    return repo


@pytest.fixture
def planner(app) -> _CountingPlanner:
    instance = _CountingPlanner()
    app.dependency_overrides[get_meal_planner] = lambda: instance
    return instance


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id, "Content-Type": "application/json"}


@pytest.fixture
def payload() -> dict:
    return {
        "ingredients": ["pasta", "tomato", "onion"],
        "days": 3,
        "meals_per_day": ["breakfast", "lunch", "dinner"],
    }


def test_second_call_with_same_input_returns_from_cache(
    client, headers, payload, fake_repo, planner
):
    first = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    second = client.post("/api/meal-plan/generate", headers=headers, json=payload)

    assert first.json()["from_cache"] is False
    assert second.json()["from_cache"] is True
    assert planner.calls == 1


def test_cache_hit_returns_same_plan_id(client, headers, payload, fake_repo, planner):
    first = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    second = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    assert first.json()["plan_id"] == second.json()["plan_id"]


def test_reordered_ingredients_hit_same_cache(client, headers, fake_repo, planner):
    a = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta", "tomato", "onion"]},
    )
    b = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["onion", "TOMATO", " pasta "]},
    )
    assert a.json()["plan_id"] == b.json()["plan_id"]
    assert b.json()["from_cache"] is True
    assert planner.calls == 1


def test_distinct_ingredients_have_distinct_cache_entries(client, headers, fake_repo, planner):
    first = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta", "tomato"]},
    )
    second = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["chicken", "rice"]},
    )
    assert first.json()["plan_id"] != second.json()["plan_id"]
    assert second.json()["from_cache"] is False
    assert planner.calls == 2
