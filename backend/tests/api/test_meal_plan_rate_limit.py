"""Rate limit tests for `POST /api/meal-plan/generate`.

The endpoint must:
- enforce `settings.rate_limit_meal_plan_per_day` (default 1) per user per day
- return 429 once the cap is reached
- never charge a cache hit against the daily quota (same pattern as vision)
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
                "ingredients": ["x"],
                "estimated_time_minutes": 5,
            }
            for i in range(15)
        ]

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        return list(self.recipes[:limit])


class _CountingPlanner:
    def __init__(self) -> None:
        self.calls = 0

    def plan(self, ingredients, profile, candidates, days=3, meals_per_day=None, max_tokens=4096):
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
                            "id": f"call{self.calls}-{day_number}-{slot}",
                            "title": "T",
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


def test_single_plan_per_day_is_default_limit(client, headers, fake_repo, planner):
    a = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta"]},
    )
    b = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["chicken"]},
    )
    assert a.status_code == 201
    assert b.status_code == 429


def test_cache_hit_does_not_consume_quota(client, headers, fake_repo, planner):
    payload = {"ingredients": ["pasta", "tomato"]}
    first = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    cached = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    distinct = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["chicken"]},
    )

    assert first.status_code == 201
    assert cached.status_code == 201
    assert cached.json()["from_cache"] is True
    # Cached request did NOT eat the only daily slot, so a NEW miss still 429s.
    assert distinct.status_code == 429
    assert planner.calls == 1


def test_rate_limit_uses_config_value(client, headers, fake_repo, planner, monkeypatch):
    from infrastructure import config as config_module

    monkeypatch.setattr(config_module.settings, "rate_limit_meal_plan_per_day", 2)

    a = client.post("/api/meal-plan/generate", headers=headers, json={"ingredients": ["a"]})
    b = client.post("/api/meal-plan/generate", headers=headers, json={"ingredients": ["b"]})
    c = client.post("/api/meal-plan/generate", headers=headers, json={"ingredients": ["c"]})
    assert a.status_code == 201
    assert b.status_code == 201
    assert c.status_code == 429
