"""`X-User-Id` request dependency.

We rely on a FastAPI dependency rather than a true ASGI middleware:
- The dependency declares the header in OpenAPI (so it shows up at `/docs`).
- It reads + validates the header and returns the user id, ready to inject.
- It raises HTTP 400 for missing or malformed values, matching the spec.

Clients (Android, web) generate a UUID v4 on first launch, persist it locally
and send it on every request. The server uses it as the profile primary key —
no auth bootstrap, no race on first write, anonymous-by-design.

The folder is named `middleware/` for organizational clarity even though the
implementation is a dependency, not an ASGI middleware.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Header, HTTPException, status


def require_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """Validate and return the `X-User-Id` header.

    Raises HTTPException(400) when the header is missing, empty, or not a
    valid UUID. Accepts any UUID format (v4 is what clients are expected to
    send, but parsing tolerates any version because rejection of older
    versions would buy nothing here).
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-User-Id header",
        )
    try:
        UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id header is not a valid UUID",
        ) from exc
    return x_user_id
