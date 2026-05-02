"""Vision endpoint: extract ingredients from an uploaded image.

Phase 2 lands the vision pipeline incrementally. This file currently ships:
- Upload validation against the configured size/format/dimension caps.
- SHA-256 hash of the image bytes.
- Hash-based `LLMCache` lookup → cached response on hit (kind="vision").
- Synchronous call into the active `VisionExtractor` on miss, then normalize
  via `IngredientReasoner` and persist to the cache with the configured TTL.

The daily rate limiter is wired in the next commit.
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
from infrastructure.storage.llm_cache import LLMCache
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
    """Validate the upload, hash the bytes, hit cache or call extractor."""
    image_bytes = validate_image_upload(image, settings)
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    cache = LLMCache(session)
    cache_key = cache.make_key("vision", image_hash)

    cached = cache.get(cache_key)
    if cached is not None:
        return VisionExtractResponse(
            ingredients=[DetectedIngredient(**item) for item in cached["ingredients"]],
            image_hash=image_hash,
            from_cache=True,
            remaining_calls_today=settings.rate_limit_vision_per_day,
        )

    language = _resolve_language(session, user_id)
    detected = extractor.extract(
        image_bytes=image_bytes,
        language=language,
        max_tokens=settings.anthropic_max_tokens_vision,
    )
    normalized = reasoner.normalize(detected, language=language)

    cache.set(
        cache_key,
        kind="vision",
        payload={"ingredients": normalized},
        ttl_seconds=settings.cache_ttl_vision_seconds,
    )

    return VisionExtractResponse(
        ingredients=[DetectedIngredient(**item) for item in normalized],
        image_hash=image_hash,
        from_cache=False,
        remaining_calls_today=settings.rate_limit_vision_per_day,
    )
