"""Meal plan endpoint request/response models.

Phase 3 fixes the meal-plan structure to 3 days × 3 slots
(breakfast/lunch/dinner). Both the request and response models pin those
constraints; non-canonical inputs are rejected at the validation layer rather
than reaching the planner. The slot ordering is enforced at the repository
projection layer (`to_response_dict`).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MealPlanRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1)
    days: int = Field(default=3, ge=3, le=3)
    meals_per_day: list[str] = Field(
        default_factory=lambda: ["breakfast", "lunch", "dinner"],
    )


class MealPlanRecipe(BaseModel):
    id: str
    title: str
    title_es: str | None = None
    estimated_time_minutes: int
    match_percentage: float = Field(ge=0.0, le=1.0)
    ingredients_summary: list[str]
    personalized_note: str | None = None


class MealSlot(BaseModel):
    slot: str = Field(pattern="^(breakfast|lunch|dinner)$")
    recipe: MealPlanRecipe


class MealPlanDay(BaseModel):
    day_number: int = Field(ge=1, le=3)
    meals: list[MealSlot]


class MealPlanResponse(BaseModel):
    plan_id: str
    user_id: str
    language: str
    created_at: datetime
    days: list[MealPlanDay]
    ingredient_reuse_score: float = Field(ge=0.0, le=1.0)
    variety_score: float = Field(ge=0.0, le=1.0)
    macro_alignment_score: float = Field(ge=0.0, le=1.0)
    from_cache: bool
