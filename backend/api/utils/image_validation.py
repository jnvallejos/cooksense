"""Image upload validation for the vision endpoint.

`validate_image_upload` reads the bytes off an `UploadFile`, refuses payloads
above `settings.image_max_size_bytes`, checks the format against the parsed
allow-list, and verifies the decoded dimensions fit
`[image_min_dimension, image_max_dimension]`. Any violation raises
`HTTPException(400)` so the route just propagates it.

Pillow is used header-style: we open the bytes in memory and let Pillow's
sniffing pick the format (this is how it identifies JPEG vs PNG vs WebP),
then read the dimensions without forcing a full decode.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

if TYPE_CHECKING:
    from infrastructure.config import Settings

_PIL_FORMAT_ALIASES = {
    "jpeg": {"jpeg", "jpg"},
    "png": {"png"},
    "webp": {"webp"},
}


def _allowed_pil_formats(setting_value: str) -> set[str]:
    """Expand the comma-separated config value into Pillow format identifiers."""
    allowed: set[str] = set()
    for token in setting_value.split(","):
        token = token.strip().lower()
        if not token:
            continue
        allowed |= _PIL_FORMAT_ALIASES.get(token, {token})
    return allowed


def validate_image_upload(file: UploadFile, settings: Settings) -> bytes:
    """Read + validate an uploaded image. Returns its raw bytes.

    Raises `HTTPException(400)` for any oversize, format, or dimension
    violation. The caller does not need to catch — fastapi turns the
    exception into the 400 response automatically.
    """
    data = _read_bytes(file)

    if len(data) > settings.image_max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"image size {len(data)} exceeds max {settings.image_max_size_bytes}",
        )

    allowed_formats = _allowed_pil_formats(settings.image_allowed_formats)

    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = (img.format or "").lower()
            width, height = img.size
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="image bytes are not a valid image") from exc

    if fmt not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"image format {fmt!r} not allowed (expected {sorted(allowed_formats)})",
        )

    smallest = min(width, height)
    largest = max(width, height)
    if smallest < settings.image_min_dimension:
        raise HTTPException(
            status_code=400,
            detail=(
                f"image dimension too small: {width}x{height} (min {settings.image_min_dimension})"
            ),
        )
    if largest > settings.image_max_dimension:
        raise HTTPException(
            status_code=400,
            detail=(
                f"image dimension too large: {width}x{height} (max {settings.image_max_dimension})"
            ),
        )

    return data


def _read_bytes(file: UploadFile) -> bytes:
    """Read bytes from an UploadFile-like object (sync or async)."""
    underlying = getattr(file, "file", None)
    if underlying is not None:
        try:
            underlying.seek(0)
        except (AttributeError, ValueError):
            pass
        return underlying.read()
    raise HTTPException(status_code=400, detail="image upload is empty or unreadable")
