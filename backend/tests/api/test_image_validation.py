"""Tests for `validate_image_upload`.

The utility reads bytes from an `UploadFile`, checks the MIME against the
configured allowed list, refuses oversize payloads, and verifies dimensions
fit `[image_min_dimension, image_max_dimension]` via Pillow.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi import HTTPException
from PIL import Image

from api.utils.image_validation import validate_image_upload
from infrastructure.config import Settings

FIXTURES = Path(__file__).parent.parent / "fixtures" / "images"


class _FakeUpload:
    """Minimal stand-in for fastapi `UploadFile` carrying bytes + metadata."""

    def __init__(
        self,
        data: bytes,
        filename: str = "image.jpg",
        content_type: str = "image/jpeg",
    ) -> None:
        self._data = data
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(data)

    async def read(self) -> bytes:  # async to match fastapi signature
        return self._data


@pytest.fixture
def settings() -> Settings:
    return Settings()


def test_accepts_valid_jpeg(settings):
    upload = _FakeUpload((FIXTURES / "pantry_basic.jpg").read_bytes())
    data = validate_image_upload(upload, settings)
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_accepts_tiny_but_valid_image(settings):
    upload = _FakeUpload((FIXTURES / "tiny.jpg").read_bytes())
    data = validate_image_upload(upload, settings)
    assert len(data) > 0


def test_rejects_oversize_payload(settings):
    blob = b"\xff\xd8" + b"x" * (settings.image_max_size_bytes + 1)
    upload = _FakeUpload(blob)
    with pytest.raises(HTTPException) as exc:
        validate_image_upload(upload, settings)
    assert exc.value.status_code == 400
    assert "size" in exc.value.detail.lower()


def test_rejects_disallowed_format(settings):
    # GIF is not in the allowed list.
    buf = io.BytesIO()
    Image.new("RGB", (400, 400), "red").save(buf, "GIF")
    upload = _FakeUpload(buf.getvalue(), filename="image.gif", content_type="image/gif")
    with pytest.raises(HTTPException) as exc:
        validate_image_upload(upload, settings)
    assert exc.value.status_code == 400
    assert "format" in exc.value.detail.lower()


def test_rejects_dimensions_below_minimum(settings):
    buf = io.BytesIO()
    Image.new("RGB", (settings.image_min_dimension - 50, 800), "blue").save(buf, "JPEG")
    upload = _FakeUpload(buf.getvalue())
    with pytest.raises(HTTPException) as exc:
        validate_image_upload(upload, settings)
    assert exc.value.status_code == 400
    assert "dimension" in exc.value.detail.lower() or "small" in exc.value.detail.lower()


def test_rejects_dimensions_above_maximum(settings):
    too_big = settings.image_max_dimension + 1
    buf = io.BytesIO()
    Image.new("RGB", (too_big, 600), "green").save(buf, "JPEG")
    upload = _FakeUpload(buf.getvalue())
    with pytest.raises(HTTPException) as exc:
        validate_image_upload(upload, settings)
    assert exc.value.status_code == 400
    assert "dimension" in exc.value.detail.lower() or "large" in exc.value.detail.lower()


def test_rejects_non_image_bytes(settings):
    upload = _FakeUpload(b"not an image at all", filename="x.jpg")
    with pytest.raises(HTTPException) as exc:
        validate_image_upload(upload, settings)
    assert exc.value.status_code == 400
