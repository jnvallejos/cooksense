"""Tests for the public stub `MealPlanner`.

The stub picks 9 random recipes from the candidate pool and returns neutral
0.5 scores. When the pool is too small, it pads with bilingual placeholder
entries so the public demo always returns a complete plan.
"""

from __future__ import annotations

from stub import MealPlanner


def _candidates(count: int) -> list[dict]:
    return [
        {
            "id": f"r{i:03d}",
            "title": f"Recipe {i}",
            "title_es": f"Receta {i}",
            "estimated_time_minutes": 10 + i,
            "ingredients": [f"ing{i}-1", f"ing{i}-2", f"ing{i}-3", f"ing{i}-4"],
        }
        for i in range(count)
    ]


def test_returns_three_days_with_three_meals_each():
    plan = MealPlanner().plan(ingredients=["pasta"], profile={}, candidates=_candidates(50))
    assert len(plan["days"]) == 3
    for day in plan["days"]:
        assert len(day["meals"]) == 3


def test_uses_canonical_slot_order():
    plan = MealPlanner().plan(ingredients=["pasta"], profile={}, candidates=_candidates(20))
    for day in plan["days"]:
        assert [m["slot"] for m in day["meals"]] == ["breakfast", "lunch", "dinner"]


def test_returns_neutral_scores():
    plan = MealPlanner().plan(ingredients=["pasta"], profile={}, candidates=_candidates(20))
    assert plan["ingredient_reuse_score"] == 0.5
    assert plan["variety_score"] == 0.5
    assert plan["macro_alignment_score"] == 0.5
    for day in plan["days"]:
        for meal in day["meals"]:
            assert meal["recipe"]["match_percentage"] == 0.5


def test_pads_when_pool_smaller_than_requested_slots():
    plan = MealPlanner().plan(
        ingredients=["pasta", "rice", "egg"],
        profile={},
        candidates=_candidates(2),
    )
    titles = [meal["recipe"]["title"] for day in plan["days"] for meal in day["meals"]]
    placeholder_count = sum(1 for t in titles if "Demo recipe" in t)
    assert placeholder_count == 7  # 9 slots minus the 2 real candidates


def test_pads_with_bilingual_placeholder_titles():
    plan = MealPlanner().plan(ingredients=["pasta"], profile={}, candidates=[])
    placeholder = plan["days"][0]["meals"][0]["recipe"]
    assert "Demo recipe" in placeholder["title"]
    assert "Receta demo" in placeholder["title_es"]


def test_handles_empty_candidates_with_full_placeholder_plan():
    plan = MealPlanner().plan(ingredients=["pasta"], profile={}, candidates=[])
    total_meals = sum(len(d["meals"]) for d in plan["days"])
    assert total_meals == 9


def test_ingredients_summary_truncated_to_three():
    plan = MealPlanner().plan(
        ingredients=["pasta", "rice", "egg", "tomato"],
        profile={},
        candidates=_candidates(10),
    )
    for day in plan["days"]:
        for meal in day["meals"]:
            assert len(meal["recipe"]["ingredients_summary"]) <= 3
