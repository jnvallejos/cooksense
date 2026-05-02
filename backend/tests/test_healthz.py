"""Tests for healthz endpoint."""


def test_healthz_returns_200_ok(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200


def test_healthz_returns_status_ok(client):
    response = client.get("/api/healthz")
    body = response.json()
    assert body["status"] == "ok"


def test_healthz_returns_service_name(client):
    response = client.get("/api/healthz")
    body = response.json()
    assert body["service"] == "cooksense-backend"


def test_healthz_response_is_json(client):
    response = client.get("/api/healthz")
    assert response.headers["content-type"].startswith("application/json")
