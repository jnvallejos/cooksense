"""Recipe endpoints.

Phase 2 extends `POST /api/recipes/search` with LLM-personalized descriptions
on the top-N results. Personalization is keyed by `(recipe_id, profile signature)`
so two users with identical profiles share a cached sentence per recipe.

Phase 1 contract still holds: the route validates `X-User-Id`, fetches up to
20 candidates from ChromaDB, runs them through `RecipeRanker.rank`, and
returns the top `limit`. Phase 2 adds a personalized description to the first
`settings.personalize_top_n_recipes` of those results; the rest leave the
field at None.
"""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import (
    PersonalizedDescriber,
    QAResponder,
    RecipeRanker,
    get_personalized_describer,
    get_qa_responder,
    get_recipe_ranker,
    get_recipe_repository,
)
from api.middleware.user_id import require_user_id
from api.models.qa import RecipeAnswerResponse, RecipeQuestionRequest
from api.models.recipe import Recipe
from api.models.search import RecipeSearchRequest, RecipeSearchResponse
from infrastructure.config import settings
from infrastructure.db.recipe_repository import RecipeRepository
from infrastructure.storage.daily_usage import DailyUsageLimiter, RateLimitExceeded
from infrastructure.storage.llm_cache import LLMCache
from infrastructure.storage.models import UserDailyUsage
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


def _profile_signature(profile: dict) -> str:
    """SHA-256 over the profile fields that influence personalization.

    We deliberately ignore household_size, fitness_goal and other fields the
    describer prompt does not consume: changes there should not invalidate
    cache entries.
    """
    canonical = {
        "skill": profile.get("cooking_skill"),
        "time_budget_minutes": profile.get("time_budget_minutes"),
        "dietary_restrictions": sorted(profile.get("dietary_restrictions") or []),
        "language": profile.get("language"),
    }
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _match_percentage(recipe: dict, query_ingredients: list[str]) -> float:
    """Fraction of recipe ingredients found in the query (case-insensitive substring)."""
    ingredients = recipe.get("ingredients") or []
    if not ingredients:
        return 0.0
    query_lower = [i.lower() for i in query_ingredients]
    hits = sum(1 for item in ingredients if any(token in item.lower() for token in query_lower))
    return hits / len(ingredients)


def _to_recipe(
    raw: dict,
    query_ingredients: list[str],
    personalized_description: str | None = None,
) -> Recipe:
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
        score=raw.get("score", 1.0),
        personalized_description=personalized_description,
    )


def _personalize(
    recipes: list[dict],
    profile: dict,
    describer: PersonalizedDescriber,
    cache: LLMCache,
) -> dict[str, str]:
    """Return `{recipe_id: description}` for `recipes`, hitting the cache first."""
    profile_sig = _profile_signature(profile)
    descriptions: dict[str, str] = {}
    for recipe in recipes:
        cache_key = cache.make_key("personalize", recipe["id"], profile_sig)
        cached = cache.get(cache_key)
        if cached is not None:
            descriptions[recipe["id"]] = cached["description"]
            continue

        description = describer.describe(
            recipe,
            profile,
            max_tokens=settings.anthropic_max_tokens_personalization,
        )
        cache.set(
            cache_key,
            kind="personalize",
            payload={"description": description},
            ttl_seconds=settings.cache_ttl_personalization_seconds,
        )
        descriptions[recipe["id"]] = description
    return descriptions


@router.post("/search", response_model=RecipeSearchResponse)
def search_recipes(
    payload: RecipeSearchRequest,
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
    repo: RecipeRepository = Depends(get_recipe_repository),
    ranker: RecipeRanker = Depends(get_recipe_ranker),
    describer: PersonalizedDescriber = Depends(get_personalized_describer),
) -> RecipeSearchResponse:
    """Return up to `payload.limit` recipes, top-N personalized by the LLM."""
    profile = _resolve_profile(session, user_id)

    candidates = repo.query_by_ingredients(payload.ingredients, limit=20)
    ranked = ranker.rank(candidates, profile, query_ingredients=payload.ingredients)
    selected = ranked[: payload.limit]

    top_n = min(settings.personalize_top_n_recipes, len(selected))
    descriptions = _personalize(selected[:top_n], profile, describer, LLMCache(session))

    recipes = [
        _to_recipe(c, payload.ingredients, descriptions.get(c["id"]))
        for c in selected
    ]

    return RecipeSearchResponse(
        recipes=recipes,
        total_found=len(candidates),
        query_id=str(uuid4()),
    )


def _qa_calls_today(session: Session, user_id: str) -> int:
    from datetime import date

    row = session.get(UserDailyUsage, (user_id, date.today()))
    return row.qa_calls if row is not None else 0


def _hash_question(question: str) -> str:
    return hashlib.sha256(question.lower().strip().encode("utf-8")).hexdigest()


def _hash_previous_questions(items: list[dict]) -> str:
    canonical = json.dumps(
        [{"q": item["question"], "a": item["answer"]} for item in items],
        sort_keys=False,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@router.post("/{recipe_id}/ask", response_model=RecipeAnswerResponse)
def ask_recipe_question(
    recipe_id: str,
    payload: RecipeQuestionRequest,
    user_id: str = Depends(require_user_id),
    session: Session = Depends(get_session),
    repo: RecipeRepository = Depends(get_recipe_repository),
    responder: QAResponder = Depends(get_qa_responder),
) -> RecipeAnswerResponse:
    """Conversational follow-up on a recipe.

    Loads the recipe (404 on miss), truncates `previous_questions` to
    `qa_max_previous_questions`, hits the response cache keyed by
    (recipe, question, history), and otherwise consumes one slot of the user's
    daily QA quota before invoking the responder.
    """
    recipe = repo.get_by_id(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"recipe {recipe_id!r} not found")

    history_cap = settings.qa_max_previous_questions
    truncated_history = [
        {"question": item.question, "answer": item.answer}
        for item in payload.previous_questions[-history_cap:]
    ]

    profile = _resolve_profile(session, user_id)
    language = profile["language"]

    cache = LLMCache(session)
    cache_key = cache.make_key(
        "qa",
        recipe_id,
        _hash_question(payload.question),
        _hash_previous_questions(truncated_history),
        language,
    )

    cached = cache.get(cache_key)
    if cached is not None:
        remaining = max(
            settings.rate_limit_qa_per_day - _qa_calls_today(session, user_id),
            0,
        )
        return RecipeAnswerResponse(
            answer=cached["answer"],
            from_cache=True,
            remaining_questions_today=remaining,
        )

    limiter = DailyUsageLimiter(session)
    try:
        remaining = limiter.check_and_increment(
            user_id, kind="qa", limit=settings.rate_limit_qa_per_day
        )
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    answer = responder.answer(
        recipe,
        payload.question,
        truncated_history,
        language=language,
        max_tokens=settings.anthropic_max_tokens_qa,
    )

    cache.set(
        cache_key,
        kind="qa",
        payload={"answer": answer},
        ttl_seconds=settings.cache_ttl_qa_seconds,
    )

    return RecipeAnswerResponse(
        answer=answer,
        from_cache=False,
        remaining_questions_today=remaining,
    )
