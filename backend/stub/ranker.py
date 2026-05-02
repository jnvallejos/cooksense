"""Stub implementation of RecipeRanker."""


class RecipeRanker:
    """Naive recipe ranker: returns recipes in input order, all with score=1.0.

    Real implementation in cooksense-core applies multi-factor scoring:
    profile-aware ingredient overlap, time budget, skill level, dietary
    restrictions, macro alignment. The signature accepts an optional
    `query_ingredients` argument for forward-compatibility with the real
    ranker; the stub ignores it.
    """

    def __init__(self) -> None:
        pass

    def rank(
        self,
        recipes: list[dict],
        profile: dict,
        query_ingredients: list[str] | None = None,
    ) -> list[dict]:
        """Return recipes in input order with `score=1.0` added to each.

        We mutate the input list in place rather than returning fresh dicts so
        callers that compare `result == recipes` still see equal values. The
        score field is harmless for downstream consumers.
        """
        for recipe in recipes:
            recipe.setdefault("score", 1.0)
        return recipes
