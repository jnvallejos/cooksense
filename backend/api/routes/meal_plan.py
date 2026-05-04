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

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import (
    IngredientReasoner,
    MealPlanner,
    get_ingredient_reasoner,
    get_meal_planner,
    get_recipe_repository,
)
from api.middleware.user_id import require_user_id
from api.models.meal_plan import MealPlanRequest, MealPlanResponse
from infrastructure.config import settings
from infrastructure.db.recipe_repository import RecipeRepository
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

    return MealPlanResponse(
        plan_id=str(uuid4()),
        user_id=user_id,
        language=profile["language"],
        created_at=datetime.now(UTC),
        days=plan["days"],
        ingredient_reuse_score=plan["ingredient_reuse_score"],
        variety_score=plan["variety_score"],
        macro_alignment_score=plan["macro_alignment_score"],
        from_cache=False,
    )
