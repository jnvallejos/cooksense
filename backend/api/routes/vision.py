"""Vision endpoint: extract ingredients from an uploaded image.

Flow:
1. Validate the multipart upload against `settings.image_*` caps.
2. Compute SHA-256 of the bytes — used as `image_hash` and as the cache key
   (so identical images always reuse the same response).
3. Look up `LLMCache(kind="vision", image_hash)`. Hit → return cached
   ingredients with `from_cache=true`. Cache hits do NOT consume quota; the
   user is billed for the underlying LLM call only.
4. Miss → check `DailyUsageLimiter`. Over → 429.
5. Increment usage, call the active `VisionExtractor`, normalize via
   `IngredientReasoner`, persist the result with `cache_ttl_vision_seconds`.
6. Return the normalized list with `remaining_calls_today` reflecting
   today's usage.

All caps, models, TTLs, and limits come from `settings`. Endpoints don't
hardcode any tunable.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
from infrastructure.storage.daily_usage import DailyUsageLimiter, RateLimitExceeded
from infrastructure.storage.llm_cache import LLMCache
from infrastructure.storage.models import UserDailyUsage
from infrastructure.storage.postgres import get_session
from infrastructure.storage.profile_repository import ProfileRepository

router = APIRouter(prefix="/api/vision", tags=["vision"])


def _resolve_language(session: Session, user_id: str) -> str:
    profile = ProfileRepository(session).get(user_id)
    return profile.language if profile is not None else "en"


def _vision_calls_today(session: Session, user_id: str) -> int:
    from datetime import date

    row = session.get(UserDailyUsage, (user_id, date.today()))
    return row.vision_calls if row is not None else 0


@router.post("/extract-ingredients", response_model=VisionExtractResponse)
def extract_ingredients(
    image: UploadFile = File(...),
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
    extractor: VisionExtractor = Depends(get_vision_extractor),
    reasoner: IngredientReasoner = Depends(get_ingredient_reasoner),
) -> VisionExtractResponse:
    """Validate, hash, hit cache or call extractor under daily quota."""
    image_bytes = validate_image_upload(image, settings)
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    cache = LLMCache(session)
    cache_key = cache.make_key("vision", image_hash)

    cached = cache.get(cache_key)
    if cached is not None:
        remaining = max(
            settings.rate_limit_vision_per_day - _vision_calls_today(session, user_id),
            0,
        )
        return VisionExtractResponse(
            ingredients=[DetectedIngredient(**item) for item in cached["ingredients"]],
            image_hash=image_hash,
            from_cache=True,
            remaining_calls_today=remaining,
        )

    limiter = DailyUsageLimiter(session)
    try:
        remaining = limiter.check_and_increment(
            user_id, kind="vision", limit=settings.rate_limit_vision_per_day
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
        ) from exc

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
        remaining_calls_today=remaining,
    )
