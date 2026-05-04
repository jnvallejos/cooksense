"""Tests for `MealPlanRepository`.

The repository is the single integration point between the meal plan endpoint
and the database. Tests cover persistence (save + recipes in one transaction),
retrieval, ownership checks, cascade delete, and the API response projection.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.storage.meal_plan_repository import MealPlanRepository
from infrastructure.storage.models import Base, MealPlan, MealPlanRecipe

PLAN = "00000000-0000-0000-0000-000000000001"
USER = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()


def _plan_payload() -> dict:
    return {
        "days": [
            {
                "day_number": 1,
                "meals": [
                    {
                        "slot": "breakfast",
                        "recipe": {
                            "id": "r1",
                            "title": "Eggs",
                            "title_es": "Huevos",
                            "estimated_time_minutes": 10,
                            "match_percentage": 0.5,
                            "ingredients_summary": ["egg", "salt"],
                            "personalized_note": "Quick.",
                        },
                    },
                    {
                        "slot": "lunch",
                        "recipe": {
                            "id": "r2",
                            "title": "Salad",
                            "title_es": "Ensalada",
                            "estimated_time_minutes": 15,
                            "match_percentage": 0.6,
                            "ingredients_summary": ["lettuce"],
                            "personalized_note": "Fresh.",
                        },
                    },
                    {
                        "slot": "dinner",
                        "recipe": {
                            "id": "r3",
                            "title": "Pasta",
                            "title_es": "Pasta",
                            "estimated_time_minutes": 20,
                            "match_percentage": 0.7,
                            "ingredients_summary": ["pasta", "tomato"],
                            "personalized_note": "Filling.",
                        },
                    },
                ],
            },
        ],
        "ingredient_reuse_score": 0.42,
        "variety_score": 0.55,
        "macro_alignment_score": 0.61,
    }


def test_save_persists_plan_and_recipes(session):
    repo = MealPlanRepository(session)
    repo.save(
        plan_id=PLAN,
        user_id=USER,
        pantry=["egg", "lettuce", "pasta"],
        days=1,
        meals_per_day=["breakfast", "lunch", "dinner"],
        language="en",
        plan_payload=_plan_payload(),
    )

    plan = session.execute(select(MealPlan).where(MealPlan.plan_id == PLAN)).scalar_one()
    assert plan.user_id == USER
    assert plan.pantry_ingredients == ["egg", "lettuce", "pasta"]
    assert plan.days == 1
    assert plan.meals_per_day == ["breakfast", "lunch", "dinner"]
    assert plan.language == "en"
    assert plan.ingredient_reuse_score == 0.42
    assert plan.variety_score == 0.55
    assert plan.macro_alignment_score == 0.61

    recipes = session.execute(select(MealPlanRecipe).order_by(MealPlanRecipe.id)).scalars().all()
    assert [r.slot for r in recipes] == ["breakfast", "lunch", "dinner"]
    assert [r.recipe_id for r in recipes] == ["r1", "r2", "r3"]
    assert recipes[0].recipe_data["title"] == "Eggs"
    assert recipes[0].personalized_note == "Quick."


def test_get_returns_plan_with_recipes(session):
    repo = MealPlanRepository(session)
    repo.save(
        plan_id=PLAN,
        user_id=USER,
        pantry=[],
        days=1,
        meals_per_day=["breakfast", "lunch", "dinner"],
        language="en",
        plan_payload=_plan_payload(),
    )

    plan = repo.get_by_id(PLAN)
    assert plan is not None
    assert plan.plan_id == PLAN
    assert len(plan.recipes) == 3
    assert {r.slot for r in plan.recipes} == {"breakfast", "lunch", "dinner"}


def test_get_returns_none_for_missing_plan_id(session):
    repo = MealPlanRepository(session)
    assert repo.get_by_id("does-not-exist") is None


def test_is_owner_returns_true_for_owning_user(session):
    repo = MealPlanRepository(session)
    repo.save(
        plan_id=PLAN,
        user_id=USER,
        pantry=[],
        days=1,
        meals_per_day=["breakfast", "lunch", "dinner"],
        language="en",
        plan_payload=_plan_payload(),
    )
    assert repo.is_owner(PLAN, USER) is True


def test_is_owner_returns_false_for_other_user(session):
    repo = MealPlanRepository(session)
    repo.save(
        plan_id=PLAN,
        user_id=USER,
        pantry=[],
        days=1,
        meals_per_day=["breakfast", "lunch", "dinner"],
        language="en",
        plan_payload=_plan_payload(),
    )
    assert repo.is_owner(PLAN, OTHER) is False


def test_is_owner_returns_false_for_missing_plan(session):
    repo = MealPlanRepository(session)
    assert repo.is_owner("nope", USER) is False


def test_cascade_delete_recipes_when_plan_deleted(session):
    repo = MealPlanRepository(session)
    repo.save(
        plan_id=PLAN,
        user_id=USER,
        pantry=[],
        days=1,
        meals_per_day=["breakfast", "lunch", "dinner"],
        language="en",
        plan_payload=_plan_payload(),
    )

    plan = repo.get_by_id(PLAN)
    assert plan is not None
    session.delete(plan)
    session.commit()

    assert session.execute(select(MealPlan)).first() is None
    assert session.execute(select(MealPlanRecipe)).first() is None
