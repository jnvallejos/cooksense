"""User profile endpoints.

`POST /api/profile` upserts the profile keyed by `X-User-Id`. `GET /api/profile/me`
reads the current user's profile. Both endpoints require a valid UUID header.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from api.middleware.user_id import require_user_id
from api.models.profile import ProfileRequest, ProfileResponse
from infrastructure.storage.models import UserProfile
from infrastructure.storage.postgres import get_session
from infrastructure.storage.profile_repository import ProfileRepository

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _to_response(profile: UserProfile) -> ProfileResponse:
    return ProfileResponse(
        user_id=profile.user_id,
        cooking_for=profile.cooking_for,
        household_size=profile.household_size,
        dietary_restrictions=list(profile.dietary_restrictions or []),
        fitness_goal=profile.fitness_goal,
        cooking_skill=profile.cooking_skill,
        time_budget_minutes=profile.time_budget_minutes,
        language=profile.language,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.post(
    "",
    response_model=ProfileResponse,
    responses={
        200: {"description": "Profile updated"},
        201: {"description": "Profile created"},
    },
)
def upsert_profile(
    payload: ProfileRequest,
    response: Response,
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """Create or update the profile for the user identified by `X-User-Id`."""
    repo = ProfileRepository(session)
    existed = repo.get(user_id) is not None
    profile = repo.upsert(user_id, payload.model_dump())
    response.status_code = status.HTTP_200_OK if existed else status.HTTP_201_CREATED
    return _to_response(profile)


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """Return the profile for the user identified by `X-User-Id`."""
    repo = ProfileRepository(session)
    profile = repo.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _to_response(profile)
