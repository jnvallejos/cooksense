"""Validation tests for `POST /api/recipes/search`.

These tests use a fake `RecipeRepository` injected via the FastAPI
dependency-override system, so no embedding model is loaded and no real
ChromaDB collection is touched. The integration with the ranker is exercised
in a separate test module.
"""

from __future__ import annotations

import pytest

from api.deps import get_recipe_repository
from api.models.recipe import Recipe


VALID_PAYLOAD = {"ingredients": ["tomato", "basil"], "limit": 5}


class _FakeRepo:
    """Returns a static recipe list regardless of ingredients."""

    def __init__(self, recipes: list[dict] | None = None) -> None:
        self._recipes = recipes or [
            {
                "id": "r1",
                "title": "Margherita Pizza",
                "title_es": "Pizza Margarita",
                "ingredients": ["tomato", "mozzarella", "basil", "dough"],
                "ingredients_es": ["tomate", "mozzarella", "albahaca", "masa"],
                "instructions": ["bake"],
                "instructions_es": ["hornear"],
                "estimated_time_minutes": 30,
                "estimated_skill": "intermediate",
            },
            {
                "id": "r2",
                "title": "Caprese Salad",
                "title_es": "Ensalada Caprese",
                "ingredients": ["tomato", "mozzarella", "basil"],
                "ingredients_es": ["tomate", "mozzarella", "albahaca"],
                "instructions": ["assemble"],
                "instructions_es": ["armar"],
                "estimated_time_minutes": 15,
                "estimated_skill": "beginner",
            },
        ]

    def query_by_ingredients(self, ingredients: list[str], limit: int = 20) -> list[dict]:
        return list(self._recipes[:limit])


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id}


@pytest.fixture
def fake_repo(app) -> _FakeRepo:
    repo = _FakeRepo()
    app.dependency_overrides[get_recipe_repository] = lambda: repo
    return repo


def test_search_returns_200_with_valid_payload(client, headers, fake_repo):
    response = client.post("/api/recipes/search", json=VALID_PAYLOAD, headers=headers)
    assert response.status_code == 200


def test_search_response_shape_matches_pydantic_model(client, headers, fake_repo):
    response = client.post("/api/recipes/search", json=VALID_PAYLOAD, headers=headers)
    body = response.json()
    assert "recipes" in body
    assert "total_found" in body
    assert "query_id" in body
    assert isinstance(body["recipes"], list)
    # Each recipe validates against the API model.
    for recipe in body["recipes"]:
        Recipe.model_validate(recipe)


def test_search_rejects_empty_ingredients(client, headers, fake_repo):
    response = client.post(
        "/api/recipes/search", json={"ingredients": [], "limit": 5}, headers=headers
    )
    assert response.status_code == 422


def test_search_rejects_missing_user_id_header(client, fake_repo):
    response = client.post("/api/recipes/search", json=VALID_PAYLOAD)
    assert response.status_code == 400


def test_search_rejects_malformed_user_id_header(client, fake_repo):
    response = client.post(
        "/api/recipes/search",
        json=VALID_PAYLOAD,
        headers={"X-User-Id": "not-uuid"},
    )
    assert response.status_code == 400


def test_search_respects_limit(client, headers, fake_repo):
    response = client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 1},
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()["recipes"]) == 1


def test_search_rejects_limit_above_twenty(client, headers, fake_repo):
    response = client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 21},
        headers=headers,
    )
    assert response.status_code == 422


def test_search_uses_profile_defaults_when_profile_missing(client, headers, fake_repo):
    """No profile written; endpoint should still respond 200 using defaults."""
    response = client.post("/api/recipes/search", json=VALID_PAYLOAD, headers=headers)
    assert response.status_code == 200
