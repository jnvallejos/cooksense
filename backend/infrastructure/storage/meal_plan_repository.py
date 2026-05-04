"""Meal plan persistence.

`MealPlanRepository` is the single integration point between the meal-plan
endpoint and the database. It owns no schema knowledge beyond the SQLAlchemy
models — callers pass plan payloads in the same shape the planner returns
(`days[]` with `meals[]` carrying `recipe` dicts).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from infrastructure.storage.models import MealPlan, MealPlanRecipe


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
