"""Tests for the `X-User-Id` request dependency.

The dependency rejects missing or malformed UUID-v4 headers with HTTP 400 and
returns the user id otherwise. We exercise it by mounting a tiny test route on
a throwaway FastAPI app so the assertions stay focused on the dependency.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.middleware.user_id import require_user_id


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/whoami")
    def whoami(user_id: str = Depends(require_user_id)) -> dict[str, str]:
        return {"user_id": user_id}

    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


VALID_UUID = "11111111-1111-1111-1111-111111111111"


def test_returns_user_id_when_header_is_valid(client):
    response = client.get("/whoami", headers={"X-User-Id": VALID_UUID})
    assert response.status_code == 200
    assert response.json() == {"user_id": VALID_UUID}


def test_rejects_missing_header(client):
    response = client.get("/whoami")
    assert response.status_code == 400


def test_rejects_malformed_uuid(client):
    response = client.get("/whoami", headers={"X-User-Id": "not-a-uuid"})
    assert response.status_code == 400


def test_rejects_empty_header(client):
    response = client.get("/whoami", headers={"X-User-Id": ""})
    assert response.status_code == 400


def test_response_body_explains_missing_header(client):
    response = client.get("/whoami")
    body = response.json()
    assert "user" in body.get("detail", "").lower() or "x-user-id" in body.get("detail", "").lower()
