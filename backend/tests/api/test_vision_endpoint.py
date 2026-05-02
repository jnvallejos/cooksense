"""Integration tests for `POST /api/vision/extract-ingredients`.

Tests use the FastAPI TestClient with `get_session` overridden to a per-test
in-memory SQLite database (see `tests/conftest.py`). The vision extractor and
ingredient reasoner are the public stubs by default.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

FIXTURES = Path(__file__).parent.parent / "fixtures" / "images"


@pytest.fixture
def headers(user_id) -> dict[str, str]:
    return {"X-User-Id": user_id}


@pytest.fixture
def image_bytes() -> bytes:
    return (FIXTURES / "pantry_basic.jpg").read_bytes()


def test_returns_200_with_ingredients(client, headers, image_bytes):
    response = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("pantry.jpg", image_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert "ingredients" in body
    assert len(body["ingredients"]) == 5  # stub returns 5
    assert body["from_cache"] is False
    assert "image_hash" in body
    assert isinstance(body["image_hash"], str) and len(body["image_hash"]) == 64


def test_each_ingredient_has_required_fields(client, headers, image_bytes):
    response = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("pantry.jpg", image_bytes, "image/jpeg")},
    )
    body = response.json()
    sample = body["ingredients"][0]
    for key in ("name", "name_es", "confidence", "estimated_quantity", "category"):
        assert key in sample


def test_rejects_missing_user_id_header(client, image_bytes):
    response = client.post(
        "/api/vision/extract-ingredients",
        files={"image": ("pantry.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 400


def test_rejects_malformed_user_id_header(client, image_bytes):
    response = client.post(
        "/api/vision/extract-ingredients",
        headers={"X-User-Id": "not-a-uuid"},
        files={"image": ("pantry.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 400


def test_rejects_missing_image(client, headers):
    response = client.post("/api/vision/extract-ingredients", headers=headers)
    assert response.status_code in (400, 422)


def test_rejects_disallowed_format(client, headers):
    buf = io.BytesIO()
    Image.new("RGB", (400, 400), "red").save(buf, "GIF")
    response = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("blob.gif", buf.getvalue(), "image/gif")},
    )
    assert response.status_code == 400


def test_rejects_oversize_payload(client, headers):
    blob = b"\xff\xd8" + b"x" * (4 * 1024 * 1024 + 10)
    response = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("huge.jpg", blob, "image/jpeg")},
    )
    assert response.status_code == 400


# --- cache ---


def test_second_call_with_same_image_returns_from_cache(client, headers, image_bytes):
    first = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("pantry.jpg", image_bytes, "image/jpeg")},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["from_cache"] is False

    second = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("pantry.jpg", image_bytes, "image/jpeg")},
    )

    assert second.status_code == 200
    second_body = second.json()
    assert second_body["from_cache"] is True
    assert second_body["image_hash"] == first_body["image_hash"]
    assert second_body["ingredients"] == first_body["ingredients"]


def test_distinct_images_yield_distinct_cache_entries(client, headers, image_bytes):
    other = (FIXTURES / "fridge_well_lit.jpg").read_bytes()
    first = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("pantry.jpg", image_bytes, "image/jpeg")},
    )
    second = client.post(
        "/api/vision/extract-ingredients",
        headers=headers,
        files={"image": ("fridge.jpg", other, "image/jpeg")},
    )

    assert first.json()["image_hash"] != second.json()["image_hash"]
    assert second.json()["from_cache"] is False


def test_cache_hit_does_not_invoke_extractor(client, headers, image_bytes, app):
    """Once a hash is cached, the second request must not call the extractor again."""
    from api.deps import get_vision_extractor

    class CountingExtractor:
        def __init__(self) -> None:
            self.calls = 0

        def extract(
            self,
            image_bytes: bytes,
            language: str = "en",
            max_tokens: int = 2048,
        ) -> list[dict]:
            self.calls += 1
            return [
                {
                    "name": "tomato",
                    "name_es": "tomate",
                    "confidence": 0.9,
                    "estimated_quantity": "1",
                    "category": "vegetable",
                }
            ]

    counting = CountingExtractor()
    app.dependency_overrides[get_vision_extractor] = lambda: counting

    files = {"image": ("pantry.jpg", image_bytes, "image/jpeg")}
    client.post("/api/vision/extract-ingredients", headers=headers, files=files)
    client.post("/api/vision/extract-ingredients", headers=headers, files=files)

    assert counting.calls == 1
