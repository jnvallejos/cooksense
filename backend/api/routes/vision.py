"""Vision endpoint: extract ingredients from an uploaded image.

Phase 2 lands the vision pipeline in three steps. This file ships step 1 —
upload validation + a synchronous call into the active `VisionExtractor`. The
hash-based cache and the daily rate limiter are wired in follow-up commits.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from api.deps import (
    IngredientReasoner,
    VisionExtractor,
    get_ingredient_reasoner,
    get_vision_extractor,
)
from api.middleware.user_id import require_user_id
from api.models.vision import DetectedIngredient, VisionExtractResponse
from api.utils.image_validation import validate_image_upload
from infrastructure.config import settings
from infrastructure.storage.postgres import get_session
from infrastructure.storage.profile_repository import ProfileRepository

router = APIRouter(prefix="/api/vision", tags=["vision"])


def _resolve_language(session: Session, user_id: str) -> str:
    profile = ProfileRepository(session).get(user_id)
    return profile.language if profile is not None else "en"


@router.post("/extract-ingredients", response_model=VisionExtractResponse)
def extract_ingredients(
    image: UploadFile = File(...),
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
    extractor: VisionExtractor = Depends(get_vision_extractor),
    reasoner: IngredientReasoner = Depends(get_ingredient_reasoner),
) -> VisionExtractResponse:
    """Validate the upload, hash the bytes, run extraction, return ingredients."""
    image_bytes = validate_image_upload(image, settings)
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    language = _resolve_language(session, user_id)
    detected = extractor.extract(
        image_bytes=image_bytes,
        language=language,
        max_tokens=settings.anthropic_max_tokens_vision,
    )
    normalized = reasoner.normalize(detected, language=language)

    return VisionExtractResponse(
        ingredients=[DetectedIngredient(**item) for item in normalized],
        image_hash=image_hash,
        from_cache=False,
        remaining_calls_today=settings.rate_limit_vision_per_day,
    )
