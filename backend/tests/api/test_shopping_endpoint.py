"""Validation tests for `POST /api/meal-plan/{plan_id}/shopping`.

The endpoint accepts an empty body, requires `X-User-Id`, and returns the
shopping list derived from a persisted plan. Ownership and 404 paths are
covered separately.
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
                "ingredients": ["x", "y", "z"],
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
        json={"ingredients": ["pasta", "tomato", "onion"]},
    )
    assert response.status_code == 201
    return response.json()["plan_id"]


def test_returns_200_with_shopping_list(client, headers, fake_repo):
    plan_id = _create_plan(client, headers)
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan_id"] == plan_id
    assert "items" in body
    assert isinstance(body["items"], list)
    assert "total_items" in body
    assert body["total_items"] == len(body["items"])
    assert body["language"] == "en"


def test_each_item_has_required_fields(client, headers, fake_repo):
    plan_id = _create_plan(client, headers)
    response = client.post(f"/api/meal-plan/{plan_id}/shopping", headers=headers)
    body = response.json()
    if body["items"]:
        sample = body["items"][0]
        for key in ("ingredient", "estimated_quantity", "category", "needed_for"):
            assert key in sample


def test_rejects_missing_user_id_header(client, fake_repo, headers):
    plan_id = _create_plan(client, headers)
    response = client.post(f"/api/meal-plan/{plan_id}/shopping")
    assert response.status_code == 400


def test_rejects_malformed_user_id_header(client, fake_repo, headers):
    plan_id = _create_plan(client, headers)
    response = client.post(
        f"/api/meal-plan/{plan_id}/shopping",
        headers={"X-User-Id": "not-a-uuid"},
    )
    assert response.status_code == 400
