"""Ownership + 404 tests for `POST /api/meal-plan/{plan_id}/shopping`."""

from __future__ import annotations

import pytest

from api.deps import get_recipe_repository

OTHER_USER = "33333333-3333-3333-3333-333333333333"


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


def test_returns_404_for_unknown_plan(client, headers, fake_repo):
    response = client.post(
        "/api/meal-plan/00000000-0000-0000-0000-000000000099/shopping",
        headers=headers,
    )
    assert response.status_code == 404


def test_returns_403_for_plan_owned_by_other_user(client, headers, fake_repo):
    create = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta", "tomato"]},
    )
    plan_id = create.json()["plan_id"]

    response = client.post(
        f"/api/meal-plan/{plan_id}/shopping",
        headers={"X-User-Id": OTHER_USER, "Content-Type": "application/json"},
    )
    assert response.status_code == 403


def test_returns_200_for_owning_user(client, headers, fake_repo):
    create = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta", "tomato"]},
    )
    plan_id = create.json()["plan_id"]
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)
    assert response.status_code == 200
