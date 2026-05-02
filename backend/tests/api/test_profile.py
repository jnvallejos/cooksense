"""Integration tests for the profile endpoints.

Tests use the FastAPI TestClient with `get_session` overridden to point at a
per-test in-memory SQLite database (see `tests/conftest.py`).
"""

from __future__ import annotations

import pytest


VALID_PAYLOAD = {
    "cooking_for": "self",
    "household_size": 1,
    "dietary_restrictions": [],
    "fitness_goal": "none",
    "cooking_skill": "beginner",
    "time_budget_minutes": 30,
    "language": "en",
}


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id}


def test_upsert_creates_new_profile_returns_201(client, headers, user_id):
    response = client.post("/api/profile", json=VALID_PAYLOAD, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == user_id
    assert body["cooking_for"] == "self"
    assert body["language"] == "en"
    assert "created_at" in body
    assert "updated_at" in body


def test_upsert_returns_200_when_profile_already_exists(client, headers):
    client.post("/api/profile", json=VALID_PAYLOAD, headers=headers)

    response = client.post(
        "/api/profile",
        json={**VALID_PAYLOAD, "cooking_skill": "pro", "time_budget_minutes": 90},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cooking_skill"] == "pro"
    assert body["time_budget_minutes"] == 90


def test_upsert_rejects_missing_user_id_header(client):
    response = client.post("/api/profile", json=VALID_PAYLOAD)
    assert response.status_code == 400


def test_upsert_rejects_malformed_user_id_header(client):
    response = client.post(
        "/api/profile",
        json=VALID_PAYLOAD,
        headers={"X-User-Id": "not-a-uuid"},
    )
    assert response.status_code == 400


def test_upsert_rejects_invalid_payload(client, headers):
    bad = {**VALID_PAYLOAD, "cooking_skill": "expert"}
    response = client.post("/api/profile", json=bad, headers=headers)
    assert response.status_code == 422  # FastAPI body validation


def test_get_me_returns_profile_for_current_user(client, headers, user_id):
    client.post("/api/profile", json=VALID_PAYLOAD, headers=headers)

    response = client.get("/api/profile/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["cooking_for"] == "self"


def test_get_me_returns_404_when_profile_missing(client, headers):
    response = client.get("/api/profile/me", headers=headers)
    assert response.status_code == 404


def test_get_me_rejects_missing_header(client):
    response = client.get("/api/profile/me")
    assert response.status_code == 400


def test_two_users_have_separate_profiles(client):
    user_a = "11111111-1111-1111-1111-111111111111"
    user_b = "22222222-2222-2222-2222-222222222222"

    client.post(
        "/api/profile",
        json={**VALID_PAYLOAD, "cooking_skill": "beginner"},
        headers={"X-User-Id": user_a},
    )
    client.post(
        "/api/profile",
        json={**VALID_PAYLOAD, "cooking_skill": "pro"},
        headers={"X-User-Id": user_b},
    )

    a = client.get("/api/profile/me", headers={"X-User-Id": user_a}).json()
    b = client.get("/api/profile/me", headers={"X-User-Id": user_b}).json()

    assert a["cooking_skill"] == "beginner"
    assert b["cooking_skill"] == "pro"
