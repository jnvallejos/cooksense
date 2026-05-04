"""Meal plan persistence.

`MealPlanRepository` is the single integration point between the meal-plan
endpoint and the database. It owns no schema knowledge beyond the SQLAlchemy
models — callers pass plan payloads in the same shape the planner returns
(`days[]` with `meals[]` carrying `recipe` dicts).
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from infrastructure.storage.models import MealPlan, MealPlanRecipe

_SLOT_ORDER = {"breakfast": 0, "lunch": 1, "dinner": 2}


class MealPlanRepository:
    """CRUD over `MealPlan` + its `MealPlanRecipe` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        plan_id: str,
        user_id: str,
        pantry: list[str],
        days: int,
        meals_per_day: list[str],
        language: str,
        plan_payload: dict,
    ) -> MealPlan:
        """Persist the plan + recipe rows in one transaction.

        `plan_payload` must carry `days[]`, `ingredient_reuse_score`,
        `variety_score`, `macro_alignment_score`. Each `days[i].meals[j]` is a
        `{slot, recipe}` pair; `recipe` is stored verbatim as JSON so the plan
        is stable even if the underlying corpus changes.
        """
        plan = MealPlan(
            plan_id=plan_id,
            user_id=user_id,
            pantry_ingredients=list(pantry),
            days=days,
            meals_per_day=list(meals_per_day),
            language=language,
            ingredient_reuse_score=plan_payload["ingredient_reuse_score"],
            variety_score=plan_payload["variety_score"],
            macro_alignment_score=plan_payload["macro_alignment_score"],
        )
        for day in plan_payload["days"]:
            for meal in day["meals"]:
                recipe = meal["recipe"]
                plan.recipes.append(
                    MealPlanRecipe(
                        day_number=day["day_number"],
                        slot=meal["slot"],
                        recipe_id=recipe["id"],
                        recipe_data=dict(recipe),
                        personalized_note=recipe.get("personalized_note"),
                    )
                )
        self._session.add(plan)
        self._session.commit()
        self._session.refresh(plan)
        return plan

    def get_by_id(self, plan_id: str) -> MealPlan | None:
        """Fetch a plan with its recipes eagerly loaded, or `None` when missing."""
        stmt = (
            select(MealPlan)
            .where(MealPlan.plan_id == plan_id)
            .options(selectinload(MealPlan.recipes))
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def is_owner(self, plan_id: str, user_id: str) -> bool:
        """Cheap ownership check that skips loading the recipe rows."""
        stmt = select(MealPlan.user_id).where(MealPlan.plan_id == plan_id)
        owner = self._session.execute(stmt).scalar_one_or_none()
        return owner == user_id if owner is not None else False

    def to_response_dict(self, plan: MealPlan) -> dict:
        """Project a `MealPlan` (+ its recipes) into the API response shape.

        Days are returned ordered by `day_number`. Within each day, slots are
        ordered by the canonical breakfast → lunch → dinner ordering rather
        than insertion order, so the API response is stable regardless of how
        the underlying rows were stored.
        """
        grouped: dict[int, list[MealPlanRecipe]] = defaultdict(list)
        for recipe in plan.recipes:
            grouped[recipe.day_number].append(recipe)

        days: list[dict] = []
        for day_number in sorted(grouped):
            meals = sorted(
                grouped[day_number], key=lambda r: _SLOT_ORDER.get(r.slot, len(_SLOT_ORDER))
            )
            days.append(
                {
                    "day_number": day_number,
                    "meals": [
                        {
                            "slot": meal.slot,
                            "recipe": _recipe_to_response(meal),
                        }
                        for meal in meals
                    ],
                }
            )

        return {
            "plan_id": plan.plan_id,
            "user_id": plan.user_id,
            "language": plan.language,
            "created_at": plan.created_at,
            "days": days,
            "ingredient_reuse_score": plan.ingredient_reuse_score,
            "variety_score": plan.variety_score,
            "macro_alignment_score": plan.macro_alignment_score,
        }


def _recipe_to_response(meal: MealPlanRecipe) -> dict:
    data = dict(meal.recipe_data or {})
    return {
        "id": meal.recipe_id,
        "title": data.get("title", ""),
        "title_es": data.get("title_es"),
        "estimated_time_minutes": data.get("estimated_time_minutes", 0),
        "match_percentage": data.get("match_percentage", 0.0),
        "ingredients_summary": list(data.get("ingredients_summary") or []),
        "personalized_note": meal.personalized_note,
    }
