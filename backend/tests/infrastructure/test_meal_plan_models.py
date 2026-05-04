"""Smoke tests for the Phase 3 SQLAlchemy models.

`MealPlan` and `MealPlanRecipe` are simple persistence objects. The repository
covers the business behavior (cascade, projection); these tests just pin the
column shape and confirm the JSON columns round-trip.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.storage.models import Base, MealPlan, MealPlanRecipe

PLAN = "00000000-0000-0000-0000-000000000001"
USER = "11111111-1111-1111-1111-111111111111"


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


def test_meal_plan_persists_and_round_trips(session):
    plan = MealPlan(
        plan_id=PLAN,
        user_id=USER,
        pantry_ingredients=["pasta", "tomato"],
        days=3,
        meals_per_day=["breakfast", "lunch", "dinner"],
        language="en",
        ingredient_reuse_score=0.5,
        variety_score=0.5,
        macro_alignment_score=0.5,
    )
    session.add(plan)
    session.commit()

    fetched = session.execute(select(MealPlan).where(MealPlan.plan_id == PLAN)).scalar_one()
    assert fetched.plan_id == PLAN
    assert fetched.user_id == USER
    assert fetched.pantry_ingredients == ["pasta", "tomato"]
    assert fetched.days == 3
    assert fetched.meals_per_day == ["breakfast", "lunch", "dinner"]
    assert fetched.language == "en"
    assert fetched.ingredient_reuse_score == 0.5
    assert fetched.variety_score == 0.5
    assert fetched.macro_alignment_score == 0.5
    assert fetched.created_at is not None


def test_meal_plan_recipe_persists_with_json_payload(session):
    session.add(
        MealPlan(
            plan_id=PLAN,
            user_id=USER,
            pantry_ingredients=[],
            days=3,
            meals_per_day=["breakfast", "lunch", "dinner"],
            language="en",
            ingredient_reuse_score=0.5,
            variety_score=0.5,
            macro_alignment_score=0.5,
        )
    )
    session.commit()

    payload = {"id": "r1", "title": "Eggs", "ingredients": ["egg"]}
    session.add(
        MealPlanRecipe(
            plan_id=PLAN,
            day_number=1,
            slot="breakfast",
            recipe_id="r1",
            recipe_data=payload,
            personalized_note="Quick.",
        )
    )
    session.commit()

    row = session.execute(select(MealPlanRecipe)).scalar_one()
    assert row.plan_id == PLAN
    assert row.day_number == 1
    assert row.slot == "breakfast"
    assert row.recipe_id == "r1"
    assert row.recipe_data == payload
    assert row.personalized_note == "Quick."


def test_meal_plan_recipe_personalized_note_optional(session):
    session.add(
        MealPlan(
            plan_id=PLAN,
            user_id=USER,
            pantry_ingredients=[],
            days=3,
            meals_per_day=["breakfast", "lunch", "dinner"],
            language="en",
            ingredient_reuse_score=0.5,
            variety_score=0.5,
            macro_alignment_score=0.5,
        )
    )
    session.commit()
    session.add(
        MealPlanRecipe(
            plan_id=PLAN,
            day_number=1,
            slot="lunch",
            recipe_id="r2",
            recipe_data={"id": "r2"},
        )
    )
    session.commit()

    row = session.execute(select(MealPlanRecipe)).scalar_one()
    assert row.personalized_note is None
