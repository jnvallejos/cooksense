"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "cooksense-backend"}
