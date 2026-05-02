"""Recipe search endpoint.

`POST /api/recipes/search` accepts an ingredient list and returns up to `limit`
candidate recipes from ChromaDB. Profile-aware ranking is applied separately
(see `feat(api): wire RecipeRanker via deps to search endpoint`); this initial
version returns the raw nearest-neighbour result with a default score.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_recipe_repository
from api.middleware.user_id import require_user_id
from api.models.recipe import Recipe
from api.models.search import RecipeSearchRequest, RecipeSearchResponse
from infrastructure.db.recipe_repository import RecipeRepository
from infrastructure.storage.postgres import get_session
from infrastructure.storage.profile_repository import ProfileRepository

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


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


def _match_percentage(recipe: dict, query_ingredients: list[str]) -> float:
    """Fraction of recipe ingredients found in the query (case-insensitive substring)."""
    ingredients = recipe.get("ingredients") or []
    if not ingredients:
        return 0.0
    query_lower = [i.lower() for i in query_ingredients]
    hits = sum(
        1 for item in ingredients if any(token in item.lower() for token in query_lower)
    )
    return hits / len(ingredients)


def _to_recipe(raw: dict, query_ingredients: list[str], score: float = 1.0) -> Recipe:
    return Recipe(
        id=raw["id"],
        title=raw.get("title", ""),
        title_es=raw.get("title_es"),
        ingredients=raw.get("ingredients") or [],
        ingredients_es=raw.get("ingredients_es"),
        instructions=raw.get("instructions") or [],
        instructions_es=raw.get("instructions_es"),
        estimated_time_minutes=raw.get("estimated_time_minutes", 0),
        estimated_skill=raw.get("estimated_skill", "intermediate"),
        match_percentage=_match_percentage(raw, query_ingredients),
        score=score,
    )


@router.post("/search", response_model=RecipeSearchResponse)
def search_recipes(
    payload: RecipeSearchRequest,
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
    repo: RecipeRepository = Depends(get_recipe_repository),
) -> RecipeSearchResponse:
    """Return up to `payload.limit` recipes that match the requested ingredients."""
    _resolve_profile(session, user_id)  # default profile is loaded for future ranking

    candidates = repo.query_by_ingredients(payload.ingredients, limit=20)
    recipes = [_to_recipe(c, payload.ingredients) for c in candidates[: payload.limit]]

    return RecipeSearchResponse(
        recipes=recipes,
        total_found=len(candidates),
        query_id=str(uuid4()),
    )
