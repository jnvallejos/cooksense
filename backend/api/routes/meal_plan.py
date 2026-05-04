"""Meal plan and shopping list endpoints.

Phase 3 surfaces two new POSTs:

* `POST /api/meal-plan/generate` — generate a 3-day, 9-meal plan from pantry
  ingredients + the user's profile. Validation rejects non-canonical
  `days`/`meals_per_day`; the canonical structure (3 × breakfast/lunch/dinner)
  is the only V1 supported shape.
* `POST /api/meal-plan/{plan_id}/shopping` — derive a shopping list from a
  persisted plan minus the pantry stored at plan creation time. Wired in a
  later commit.

All caps, models, TTLs, and rate limits read from `settings`. Endpoints don't
hardcode tunables.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import (
    IngredientReasoner,
    MealPlanner,
    ShoppingListBuilder,
    get_ingredient_reasoner,
    get_meal_planner,
    get_recipe_repository,
    get_shopping_list_builder,
)
from api.middleware.user_id import require_user_id
from api.models.meal_plan import MealPlanRequest, MealPlanResponse
from api.models.shopping import ShoppingItem, ShoppingListResponse
from infrastructure.config import settings
from infrastructure.db.recipe_repository import RecipeRepository
from infrastructure.storage.daily_usage import DailyUsageLimiter, RateLimitExceeded
from infrastructure.storage.llm_cache import LLMCache
from infrastructure.storage.meal_plan_repository import MealPlanRepository
from infrastructure.storage.postgres import get_session
from infrastructure.storage.profile_repository import ProfileRepository

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])


_DEFAULT_PROFILE = {
    "cooking_for": "self",
    "household_size": 1,
    "dietary_restrictions": [],
    "fitness_goal": "none",
    "cooking_skill": "intermediate",
    "time_budget_minutes": 30,
    "language": "en",
}


def _resolve_profile(session: Session, user_id: str) -> dict:
    profile = ProfileRepository(session).get(user_id)
    if profile is None:
        return dict(_DEFAULT_PROFILE)
    return {
        "cooking_for": profile.cooking_for,
        "household_size": profile.household_size,
        "dietary_restrictions": list(profile.dietary_restrictions or []),
        "fitness_goal": profile.fitness_goal,
        "cooking_skill": profile.cooking_skill,
        "time_budget_minutes": profile.time_budget_minutes,
        "language": profile.language,
    }


def _canonical_meals_per_day() -> list[str]:
    return [s.strip() for s in settings.meal_plan_meals_per_day.split(",") if s.strip()]


def meal_plan_signature(profile: dict) -> str:
    """SHA-256 over the profile fields that influence meal plan generation.

    Extends the search/personalization signature (`cooking_skill`,
    `time_budget_minutes`, `dietary_restrictions`, `language`) with
    `household_size` and `fitness_goal`, which the planner consumes when
    arranging meals.
    """
    canonical = {
        "skill": profile.get("cooking_skill"),
        "time_budget_minutes": profile.get("time_budget_minutes"),
        "dietary_restrictions": sorted(profile.get("dietary_restrictions") or []),
        "language": profile.get("language"),
        "household_size": profile.get("household_size"),
        "fitness_goal": profile.get("fitness_goal"),
    }
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _canonical_ingredients(ingredients: list[str]) -> str:
    return "|".join(sorted(i.lower().strip() for i in ingredients if i and i.strip()))


def _normalize_ingredients(
    raw: list[str], reasoner: IngredientReasoner, language: str
) -> list[str]:
    """Run free-text ingredient strings through the active reasoner.

    The stub reasoner is a no-op (returns each item with `category` defaulted);
    the proprietary reasoner singularizes and de-synonymizes. Either way the
    result is a flat list of canonical name strings the planner can consume.
    """
    detected = [{"name": s.lower().strip()} for s in raw if s and s.strip()]
    normalized = reasoner.normalize(detected, language=language)
    return [item["name"] for item in normalized if item.get("name")]


@router.post("/generate", response_model=MealPlanResponse, status_code=201)
def generate_meal_plan(
    payload: MealPlanRequest,
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
    repo: RecipeRepository = Depends(get_recipe_repository),
    planner: MealPlanner = Depends(get_meal_planner),
    reasoner: IngredientReasoner = Depends(get_ingredient_reasoner),
) -> MealPlanResponse:
    """Validate the request, run the planner, return a fresh plan."""
    canonical = _canonical_meals_per_day()
    if list(payload.meals_per_day) != canonical:
        raise HTTPException(
            status_code=400,
            detail=f"meals_per_day must equal {canonical!r} (V1 only)",
        )
    if payload.days != settings.meal_plan_default_days:
        raise HTTPException(
            status_code=400,
            detail=f"days must equal {settings.meal_plan_default_days} (V1 only)",
        )

    profile = _resolve_profile(session, user_id)
    plan_repo = MealPlanRepository(session)
    cache = LLMCache(session)
    cache_key = cache.make_key(
        "meal_plan", _canonical_ingredients(payload.ingredients), meal_plan_signature(profile)
    )

    cached = cache.get(cache_key)
    if cached is not None:
        cached_plan = plan_repo.get_by_id(cached["plan_id"])
        if cached_plan is not None:
            response = plan_repo.to_response_dict(cached_plan)
            return MealPlanResponse(
                plan_id=response["plan_id"],
                user_id=response["user_id"],
                language=response["language"],
                created_at=response["created_at"] or datetime.now(UTC),
                days=response["days"],
                ingredient_reuse_score=response["ingredient_reuse_score"],
                variety_score=response["variety_score"],
                macro_alignment_score=response["macro_alignment_score"],
                from_cache=True,
            )

    limiter = DailyUsageLimiter(session)
    try:
        limiter.check_and_increment(
            user_id, kind="plan", limit=settings.rate_limit_meal_plan_per_day
        )
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    norm_ingredients = _normalize_ingredients(
        payload.ingredients, reasoner, profile["language"]
    )

    candidates = repo.query_by_ingredients(
        norm_ingredients, limit=settings.meal_plan_candidate_pool_size
    )
    plan = planner.plan(
        ingredients=norm_ingredients,
        profile=profile,
        candidates=candidates,
        days=payload.days,
        meals_per_day=payload.meals_per_day,
        max_tokens=settings.anthropic_max_tokens_planning,
    )

    plan_id = str(uuid4())
    saved = plan_repo.save(
        plan_id=plan_id,
        user_id=user_id,
        pantry=norm_ingredients,
        days=payload.days,
        meals_per_day=list(payload.meals_per_day),
        language=profile["language"],
        plan_payload=plan,
    )
    cache.set(
        cache_key,
        kind="meal_plan",
        payload={"plan_id": plan_id},
        ttl_seconds=settings.cache_ttl_meal_plan_seconds,
    )

    response = plan_repo.to_response_dict(saved)
    return MealPlanResponse(
        plan_id=response["plan_id"],
        user_id=response["user_id"],
        language=response["language"],
        created_at=response["created_at"] or datetime.now(UTC),
        days=response["days"],
        ingredient_reuse_score=response["ingredient_reuse_score"],
        variety_score=response["variety_score"],
        macro_alignment_score=response["macro_alignment_score"],
        from_cache=False,
    )


@router.post("/{plan_id}/shopping", response_model=ShoppingListResponse)
def generate_shopping_list(
    plan_id: str,
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
    builder: ShoppingListBuilder = Depends(get_shopping_list_builder),
) -> ShoppingListResponse:
    """Derive the shopping list for a persisted plan.

    No caching here per spec section 4.2: derivation is fast, deterministic,
    and the LLM cost is small (~USD 0.005 per list with Haiku).
    """
    plan_repo = MealPlanRepository(session)
    plan = plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"plan {plan_id!r} not found")
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="plan does not belong to the requesting user"
        )

    profile = _resolve_profile(session, plan.user_id)
    attribution = _collect_ingredients(plan)
    items = builder.build(
        attribution,
        profile=profile,
        max_tokens=settings.anthropic_max_tokens_shopping,
    )
    shopping_items = [ShoppingItem(**item) for item in items]
    return ShoppingListResponse(
        plan_id=plan.plan_id,
        items=shopping_items,
        total_items=len(shopping_items),
        language=plan.language,
    )


def _collect_ingredients(plan) -> dict[str, list[str]]:
    attribution: dict[str, list[str]] = {}
    for recipe in plan.recipes:
        data = recipe.recipe_data or {}
        for ingredient in data.get("ingredients") or data.get("ingredients_summary") or []:
            attribution.setdefault(ingredient, []).append(recipe.recipe_id)
    return attribution
