"""Smoke tests for the cooksense-core-stub package."""

from stub import IngredientReasoner, RecipeRanker


class TestRecipeRanker:
    def test_rank_returns_recipes_unchanged(self):
        ranker = RecipeRanker()
        recipes = [{"id": "r1"}, {"id": "r2"}]
        profile = {"skill": "beginner"}

        result = ranker.rank(recipes, profile)

        assert result == recipes


class TestIngredientReasoner:
    def test_reason_returns_ingredients_unchanged(self):
        reasoner = IngredientReasoner()
        ingredients = ["tomato", "onion"]
        profile = {"diet": "vegan"}

        result = reasoner.reason(ingredients, profile)

        assert result == ingredients
