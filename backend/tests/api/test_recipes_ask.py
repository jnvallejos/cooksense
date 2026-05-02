"""Integration tests for `POST /api/recipes/{recipe_id}/ask`.

The endpoint loads the recipe from the corpus, dispatches to the active
`QAResponder` (the public stub by default), caches the answer keyed by
recipe + question + previous-question history, and enforces a per-user
daily QA quota.
"""

from __future__ import annotations

import pytest

from api.deps import get_qa_responder, get_recipe_repository
from stub.qa_responder import QAResponder


class _SingleRecipeRepo:
    """Repo that yields exactly one recipe with the given id; rejects others as 404."""

    def __init__(self, recipe_id: str) -> None:
        self._recipes = {
            recipe_id: {
                "id": recipe_id,
                "title": "Margherita Pizza",
                "title_es": "Pizza Margarita",
                "ingredients": ["tomato", "mozzarella", "basil"],
                "ingredients_es": ["tomate", "mozzarella", "albahaca"],
                "instructions": ["bake"],
                "instructions_es": ["hornear"],
                "estimated_time_minutes": 30,
                "estimated_skill": "intermediate",
            }
        }

    def query_by_ingredients(self, ingredients, limit=20):
        return list(self._recipes.values())[:limit]

    def get_by_id(self, recipe_id: str) -> dict | None:
        return self._recipes.get(recipe_id)


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id}


@pytest.fixture
def recipe_repo(app) -> _SingleRecipeRepo:
    repo = _SingleRecipeRepo("r001")
    app.dependency_overrides[get_recipe_repository] = lambda: repo
    return repo


def test_ask_returns_200_with_demo_answer(client, headers, recipe_repo):
    response = client.post(
        "/api/recipes/r001/ask",
        json={"question": "Can I substitute spinach?"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == QAResponder.DEMO_EN
    assert body["from_cache"] is False
    assert body["remaining_questions_today"] == 9


def test_ask_rejects_missing_user_id_header(client, recipe_repo):
    response = client.post("/api/recipes/r001/ask", json={"question": "?"})
    assert response.status_code == 400


def test_ask_rejects_empty_question(client, headers, recipe_repo):
    response = client.post(
        "/api/recipes/r001/ask",
        json={"question": ""},
        headers=headers,
    )
    assert response.status_code == 422


def test_ask_returns_404_for_unknown_recipe(client, headers, recipe_repo):
    response = client.post(
        "/api/recipes/does-not-exist/ask",
        json={"question": "?"},
        headers=headers,
    )
    assert response.status_code == 404


# --- cache ---


class _RecordingResponder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def answer(self, recipe, question, previous_questions, language="en", max_tokens=1024):
        self.calls.append(
            {
                "recipe_id": recipe.get("id"),
                "question": question,
                "previous_questions": list(previous_questions),
                "language": language,
            }
        )
        return f"answer for {recipe.get('id')} :: {question}"


def test_ask_caches_repeat_questions(client, headers, recipe_repo, app):
    responder = _RecordingResponder()
    app.dependency_overrides[get_qa_responder] = lambda: responder

    payload = {"question": "How long does it take?"}
    first = client.post("/api/recipes/r001/ask", json=payload, headers=headers)
    second = client.post("/api/recipes/r001/ask", json=payload, headers=headers)

    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["from_cache"] is False
    assert second.json()["from_cache"] is True
    assert second.json()["answer"] == first.json()["answer"]
    assert len(responder.calls) == 1


def test_ask_cache_separates_by_previous_history(client, headers, recipe_repo, app):
    """Same question with different prior context should miss the cache."""
    responder = _RecordingResponder()
    app.dependency_overrides[get_qa_responder] = lambda: responder

    base = {"question": "How long does it take?"}
    with_history = {
        **base,
        "previous_questions": [{"question": "Is it vegan?", "answer": "Yes"}],
    }

    client.post("/api/recipes/r001/ask", json=base, headers=headers)
    response = client.post("/api/recipes/r001/ask", json=with_history, headers=headers)

    assert response.json()["from_cache"] is False
    assert len(responder.calls) == 2


# --- rate limit ---


def test_ask_remaining_decrements_per_call(client, headers, recipe_repo):
    first = client.post(
        "/api/recipes/r001/ask",
        json={"question": "q1"},
        headers=headers,
    )
    second = client.post(
        "/api/recipes/r001/ask",
        json={"question": "q2"},
        headers=headers,
    )

    assert first.json()["remaining_questions_today"] == 9
    assert second.json()["remaining_questions_today"] == 8


def test_ask_returns_429_after_daily_limit(client, headers, recipe_repo):
    for i in range(10):
        response = client.post(
            "/api/recipes/r001/ask",
            json={"question": f"q{i}"},
            headers=headers,
        )
        assert response.status_code == 200

    response = client.post(
        "/api/recipes/r001/ask",
        json={"question": "one too many"},
        headers=headers,
    )
    assert response.status_code == 429


# --- previous_questions truncation ---


def test_ask_truncates_long_history_to_config_max(client, headers, recipe_repo, app):
    """`qa_max_previous_questions` defaults to 5; excess is truncated server-side."""
    responder = _RecordingResponder()
    app.dependency_overrides[get_qa_responder] = lambda: responder

    long_history = [
        {"question": f"q{i}", "answer": f"a{i}"}
        for i in range(8)
    ]
    response = client.post(
        "/api/recipes/r001/ask",
        json={"question": "now what?", "previous_questions": long_history},
        headers=headers,
    )

    assert response.status_code == 200
    assert len(responder.calls) == 1
    forwarded = responder.calls[0]["previous_questions"]
    assert len(forwarded) == 5
    # newest 5 kept, in original order
    assert [item["question"] for item in forwarded] == ["q3", "q4", "q5", "q6", "q7"]


def test_ask_truncation_respects_config_override(
    client, headers, recipe_repo, app, monkeypatch
):
    from infrastructure import config as config_module

    monkeypatch.setattr(config_module.settings, "qa_max_previous_questions", 2)

    responder = _RecordingResponder()
    app.dependency_overrides[get_qa_responder] = lambda: responder

    history = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(5)]
    client.post(
        "/api/recipes/r001/ask",
        json={"question": "?", "previous_questions": history},
        headers=headers,
    )

    forwarded = responder.calls[0]["previous_questions"]
    assert len(forwarded) == 2
    assert [item["question"] for item in forwarded] == ["q3", "q4"]


# --- bilingual ---


def test_ask_returns_spanish_for_es_profile(client, headers, recipe_repo):
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

    response = client.post(
        "/api/recipes/r001/ask",
        json={"question": "¿lleva ajo?"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["answer"] == QAResponder.DEMO_ES
