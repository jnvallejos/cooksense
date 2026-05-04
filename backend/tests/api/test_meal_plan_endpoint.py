"""Validation tests for `POST /api/meal-plan/generate`.

The endpoint refuses missing/malformed `X-User-Id`, empty `ingredients`,
non-canonical `days`, and non-canonical `meals_per_day` lists. Persistence,
caching, and rate-limit behavior are covered in the dedicated test files.
"""

from __future__ import annotations

import pytest


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


def test_returns_201_with_plan(client, headers, payload):
    response = client.post("/api/meal-plan/generate", headers=headers, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert "plan_id" in body
    assert body["user_id"] == headers["X-User-Id"]
    assert body["language"] == "en"
    assert len(body["days"]) == 3
    for day in body["days"]:
        assert len(day["meals"]) == 3
        assert [m["slot"] for m in day["meals"]] == ["breakfast", "lunch", "dinner"]
    assert body["from_cache"] is False
    assert "ingredient_reuse_score" in body
    assert "variety_score" in body
    assert "macro_alignment_score" in body


def test_rejects_missing_user_id_header(client, payload):
    response = client.post("/api/meal-plan/generate", json=payload)
    assert response.status_code == 400


def test_rejects_malformed_user_id_header(client, payload):
    response = client.post(
        "/api/meal-plan/generate",
        headers={"X-User-Id": "not-a-uuid"},
        json=payload,
    )
    assert response.status_code == 400


def test_rejects_empty_ingredients(client, headers):
    response = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": [], "days": 3, "meals_per_day": ["breakfast", "lunch", "dinner"]},
    )
    assert response.status_code == 400


def test_rejects_days_other_than_default(client, headers):
    body = {
        "ingredients": ["pasta"],
        "days": 5,
        "meals_per_day": ["breakfast", "lunch", "dinner"],
    }
    response = client.post("/api/meal-plan/generate", headers=headers, json=body)
    assert response.status_code == 400


def test_rejects_non_canonical_meals_per_day(client, headers):
    body = {
        "ingredients": ["pasta"],
        "days": 3,
        "meals_per_day": ["snack", "lunch", "dinner"],
    }
    response = client.post("/api/meal-plan/generate", headers=headers, json=body)
    assert response.status_code == 400


def test_defaults_apply_when_days_and_meals_omitted(client, headers):
    response = client.post(
        "/api/meal-plan/generate",
        headers=headers,
        json={"ingredients": ["pasta"]},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["days"]) == 3
