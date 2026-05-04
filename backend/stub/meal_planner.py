"""Stub implementation of MealPlanner.

Returns 9 random recipes from the candidate pool with neutral 0.5 scores. If
the pool has fewer than `days * len(meals_per_day)` recipes, the missing slots
are padded with bilingual placeholder entries so the public demo always
returns a complete plan.

The real implementation in `cooksense-core` runs dict-based scoring + ONE
Sonnet call for arrangement + template-based notes. Public consumers see only
this stub.
"""

from __future__ import annotations

import random


class MealPlanner:
    """Stub: random selection with neutral scores and demo placeholders."""

    def __init__(self, client: object | None = None, model: str = "stub") -> None:
        self.client = client
        self.model = model

    def plan(
        self,
        ingredients: list[str],
        profile: dict,
        candidates: list[dict],
        days: int = 3,
        meals_per_day: list[str] | None = None,
        max_tokens: int = 4096,
    ) -> dict:
        meals_per_day = meals_per_day or ["breakfast", "lunch", "dinner"]
        slots = days * len(meals_per_day)

        pool = list(candidates)
        random.shuffle(pool)
        selected = pool[:slots]
        while len(selected) < slots:
            selected.append(_placeholder_recipe(len(selected), ingredients))

        days_data: list[dict] = []
        idx = 0
        for day_number in range(1, days + 1):
            meals: list[dict] = []
            for slot in meals_per_day:
                recipe = selected[idx]
                meals.append(
                    {
                        "slot": slot,
                        "recipe": {
                            "id": recipe.get("id", f"stub-r{idx:03d}"),
                            "title": recipe.get("title", ""),
                            "title_es": recipe.get("title_es"),
                            "estimated_time_minutes": recipe.get("estimated_time_minutes", 30),
                            "match_percentage": 0.5,
                            "ingredients_summary": list(
                                (recipe.get("ingredients") or [])[:3]
                            ),
                            "personalized_note": "Demo placeholder.",
                        },
                    }
                )
                idx += 1
            days_data.append({"day_number": day_number, "meals": meals})

        return {
            "days": days_data,
            "ingredient_reuse_score": 0.5,
            "variety_score": 0.5,
            "macro_alignment_score": 0.5,
        }


def _placeholder_recipe(index: int, ingredients: list[str]) -> dict:
    return {
        "id": f"stub-r{index:03d}",
        "title": "Demo recipe (install cooksense-core for real)",
        "title_es": "Receta demo (instalá cooksense-core para reales)",
        "estimated_time_minutes": 30,
        "ingredients": list(ingredients[:3]),
    }
