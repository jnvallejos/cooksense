"""Smoke tests for the cooksense-core-stub package."""

from stub import IngredientReasoner, RecipeRanker


class TestRecipeRanker:
    def test_rank_returns_recipes_unchanged(self):
        ranker = RecipeRanker()
        recipes = [{"id": "r1"}, {"id": "r2"}]
        profile = {"skill": "beginner"}

        result = ranker.rank(recipes, profile)

        assert result == recipes

    def test_rank_accepts_query_ingredients_kwarg(self):
        """Extended signature: query_ingredients is optional but may be passed."""
        ranker = RecipeRanker()
        recipes = [{"id": "r1"}]
        profile = {"skill": "beginner"}

        result = ranker.rank(recipes, profile, query_ingredients=["tomato"])

        assert len(result) == 1
        assert result[0]["id"] == "r1"

    def test_rank_adds_score_field_to_each_recipe(self):
        ranker = RecipeRanker()
        recipes = [{"id": "r1"}, {"id": "r2"}]

        result = ranker.rank(recipes, profile={})

        for r in result:
            assert r["score"] == 1.0

    def test_rank_preserves_input_order(self):
        ranker = RecipeRanker()
        recipes = [{"id": "alpha"}, {"id": "beta"}, {"id": "gamma"}]

        result = ranker.rank(recipes, profile={})

        assert [r["id"] for r in result] == ["alpha", "beta", "gamma"]


class TestIngredientReasoner:
    def test_reason_returns_ingredients_unchanged(self):
        reasoner = IngredientReasoner()
        ingredients = ["tomato", "onion"]
        profile = {"diet": "vegan"}

        result = reasoner.reason(ingredients, profile)

        assert result == ingredients
