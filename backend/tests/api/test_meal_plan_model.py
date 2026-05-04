"""Validation tests for the meal plan Pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.models.meal_plan import (
    MealPlanDay,
    MealPlanRecipe,
    MealPlanRequest,
    MealPlanResponse,
    MealSlot,
)


def _recipe(**overrides) -> MealPlanRecipe:
    base = {
        "id": "r1",
        "title": "Eggs",
        "title_es": "Huevos",
        "estimated_time_minutes": 10,
        "match_percentage": 0.5,
        "ingredients_summary": ["egg"],
        "personalized_note": "note",
    }
    base.update(overrides)
    return MealPlanRecipe(**base)


def test_request_defaults():
    req = MealPlanRequest(ingredients=["pasta"])
    assert req.days == 3
    assert req.meals_per_day == ["breakfast", "lunch", "dinner"]


def test_request_rejects_empty_ingredients():
    with pytest.raises(ValidationError):
        MealPlanRequest(ingredients=[])


def test_request_rejects_days_other_than_three():
    with pytest.raises(ValidationError):
        MealPlanRequest(ingredients=["pasta"], days=2)
    with pytest.raises(ValidationError):
        MealPlanRequest(ingredients=["pasta"], days=4)


def test_meal_slot_rejects_unknown_slot():
    with pytest.raises(ValidationError):
        MealSlot(slot="snack", recipe=_recipe())


def test_meal_slot_accepts_canonical_slots():
    for name in ("breakfast", "lunch", "dinner"):
        MealSlot(slot=name, recipe=_recipe())


def test_meal_plan_day_day_number_bounds():
    with pytest.raises(ValidationError):
        MealPlanDay(day_number=0, meals=[])
    with pytest.raises(ValidationError):
        MealPlanDay(day_number=4, meals=[])


def test_meal_plan_recipe_match_percentage_bounds():
    with pytest.raises(ValidationError):
        _recipe(match_percentage=-0.1)
    with pytest.raises(ValidationError):
        _recipe(match_percentage=1.1)


def test_meal_plan_response_round_trips():
    payload = MealPlanResponse(
        plan_id="00000000-0000-0000-0000-000000000001",
        user_id="11111111-1111-1111-1111-111111111111",
        language="en",
        created_at=datetime.now(UTC),
        days=[
            MealPlanDay(
                day_number=1,
                meals=[
                    MealSlot(slot="breakfast", recipe=_recipe()),
                    MealSlot(slot="lunch", recipe=_recipe()),
                    MealSlot(slot="dinner", recipe=_recipe()),
                ],
            )
        ],
        ingredient_reuse_score=0.5,
        variety_score=0.6,
        macro_alignment_score=0.7,
        from_cache=False,
    )
    dumped = payload.model_dump()
    assert dumped["from_cache"] is False
    assert dumped["days"][0]["meals"][0]["slot"] == "breakfast"


def test_meal_plan_response_score_bounds():
    base = {
        "plan_id": "p",
        "user_id": "u",
        "language": "en",
        "created_at": datetime.now(UTC),
        "days": [],
        "ingredient_reuse_score": 1.5,
        "variety_score": 0.5,
        "macro_alignment_score": 0.5,
        "from_cache": False,
    }
    with pytest.raises(ValidationError):
        MealPlanResponse(**base)
