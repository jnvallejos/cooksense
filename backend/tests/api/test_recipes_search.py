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


# --- Ranker integration ---


class _RecordingRanker:
    """Captures the (recipes, profile, query_ingredients) triple of each call."""

    def __init__(self, returns: list[dict] | None = None) -> None:
        self.calls: list[dict] = []
        self._returns = returns

    def rank(
        self,
        recipes: list[dict],
        profile: dict,
        query_ingredients: list[str] | None = None,
    ) -> list[dict]:
        self.calls.append(
            {
                "recipes": recipes,
                "profile": profile,
                "query_ingredients": query_ingredients,
            }
        )
        if self._returns is not None:
            return self._returns
        return [{**r, "score": 1.0} for r in recipes]


@pytest.fixture
def ranker(app) -> _RecordingRanker:
    from api.deps import get_recipe_ranker

    instance = _RecordingRanker()
    app.dependency_overrides[get_recipe_ranker] = lambda: instance
    return instance


def test_search_invokes_ranker_with_query_ingredients(client, headers, fake_repo, ranker):
    payload = {"ingredients": ["tomato", "basil"], "limit": 5}
    client.post("/api/recipes/search", json=payload, headers=headers)

    assert len(ranker.calls) == 1
    assert ranker.calls[0]["query_ingredients"] == ["tomato", "basil"]


def test_search_uses_profile_when_present(client, headers, fake_repo, ranker, user_id):
    profile_payload = {
        "cooking_for": "self",
        "household_size": 1,
        "dietary_restrictions": ["vegan"],
        "fitness_goal": "none",
        "cooking_skill": "pro",
        "time_budget_minutes": 60,
        "language": "en",
    }
    client.post("/api/profile", json=profile_payload, headers=headers)

    client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 5},
        headers=headers,
    )

    assert len(ranker.calls) == 1
    profile = ranker.calls[0]["profile"]
    assert profile["cooking_skill"] == "pro"
    assert profile["dietary_restrictions"] == ["vegan"]


def test_search_uses_default_profile_when_missing(client, headers, fake_repo, ranker):
    client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 5},
        headers=headers,
    )

    profile = ranker.calls[0]["profile"]
    assert profile["cooking_skill"] == "intermediate"
    assert profile["language"] == "en"
    assert profile["dietary_restrictions"] == []


def test_search_returns_recipes_in_ranker_order(client, headers, fake_repo, app):
    """The endpoint preserves the ranker's output order rather than chroma's."""
    from api.deps import get_recipe_ranker

    reordered = [
        {
            "id": "second",
            "title": "Second",
            "ingredients": ["tomato"],
            "instructions": ["go"],
            "estimated_time_minutes": 20,
            "estimated_skill": "beginner",
            "score": 0.9,
        },
        {
            "id": "first",
            "title": "First",
            "ingredients": ["tomato"],
            "instructions": ["go"],
            "estimated_time_minutes": 20,
            "estimated_skill": "beginner",
            "score": 1.0,
        },
    ]
    ranker = _RecordingRanker(returns=reordered)
    app.dependency_overrides[get_recipe_ranker] = lambda: ranker

    response = client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    ids = [r["id"] for r in response.json()["recipes"]]
    assert ids == ["second", "first"]


# --- Personalization (Phase 2) ---


def _wider_repo() -> _FakeRepo:
    """Repo with 8 candidates so we can test the top-N personalization cap."""
    base = {
        "ingredients": ["tomato"],
        "ingredients_es": ["tomate"],
        "instructions": ["go"],
        "instructions_es": ["ir"],
        "estimated_time_minutes": 20,
        "estimated_skill": "beginner",
    }
    return _FakeRepo(
        recipes=[
            {"id": f"r{i}", "title": f"Recipe {i}", "title_es": f"Receta {i}", **base}
            for i in range(8)
        ]
    )


@pytest.fixture
def wider_repo(app) -> _FakeRepo:
    repo = _wider_repo()
    app.dependency_overrides[get_recipe_repository] = lambda: repo
    return repo


class _RecordingDescriber:
    """Records every describe() call so tests can assert top-N truncation."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def describe(self, recipe, profile, max_tokens=512):
        self.calls.append({"recipe_id": recipe.get("id"), "profile": dict(profile)})
        lang = profile.get("language", "en")
        return f"[{lang}] personalized for {recipe.get('id')}"


def test_search_personalizes_only_top_n_recipes(client, headers, wider_repo, app):
    """`personalize_top_n_recipes` defaults to 5; later results stay None."""
    from api.deps import get_personalized_describer

    describer = _RecordingDescriber()
    app.dependency_overrides[get_personalized_describer] = lambda: describer

    response = client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 8},
        headers=headers,
    )

    assert response.status_code == 200
    recipes = response.json()["recipes"]
    assert len(recipes) == 8
    described_ids = [r["id"] for r in recipes if r.get("personalized_description")]
    assert len(described_ids) == 5
    assert described_ids == [r["id"] for r in recipes[:5]]


def test_search_personalization_uses_profile_language(client, headers, wider_repo, app, user_id):
    """The describer receives the user's profile language."""
    from api.deps import get_personalized_describer

    profile_payload = {
        "cooking_for": "self",
        "household_size": 1,
        "dietary_restrictions": [],
        "fitness_goal": "none",
        "cooking_skill": "beginner",
        "time_budget_minutes": 30,
        "language": "es",
    }
    client.post("/api/profile", json=profile_payload, headers=headers)

    describer = _RecordingDescriber()
    app.dependency_overrides[get_personalized_describer] = lambda: describer

    response = client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    assert all(call["profile"]["language"] == "es" for call in describer.calls)
    assert response.json()["recipes"][0]["personalized_description"].startswith("[es]")


def test_search_personalization_is_cached_across_calls(client, headers, wider_repo, app):
    """Identical (recipe, profile_signature) hits the cache instead of describing again."""
    from api.deps import get_personalized_describer

    describer = _RecordingDescriber()
    app.dependency_overrides[get_personalized_describer] = lambda: describer

    payload = {"ingredients": ["tomato"], "limit": 5}
    client.post("/api/recipes/search", json=payload, headers=headers)
    first_calls = len(describer.calls)

    client.post("/api/recipes/search", json=payload, headers=headers)
    second_calls = len(describer.calls)

    assert first_calls == 5
    assert second_calls == first_calls  # second request fully served from cache


def test_search_personalization_respects_top_n_config(
    client, headers, wider_repo, app, monkeypatch
):
    """Config drives personalization — never hardcoded."""
    from api.deps import get_personalized_describer
    from infrastructure import config as config_module

    monkeypatch.setattr(config_module.settings, "personalize_top_n_recipes", 2)

    describer = _RecordingDescriber()
    app.dependency_overrides[get_personalized_describer] = lambda: describer

    response = client.post(
        "/api/recipes/search",
        json={"ingredients": ["tomato"], "limit": 6},
        headers=headers,
    )

    assert response.status_code == 200
    recipes = response.json()["recipes"]
    described = [r for r in recipes if r.get("personalized_description")]
    assert len(described) == 2
