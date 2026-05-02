"""Stub implementation of RecipeRanker."""


class RecipeRanker:
    """Naive recipe ranker: returns recipes in input order, unweighted.

    Real implementation in cooksense-core applies multi-factor scoring:
    profile-aware ingredient overlap, time budget, skill level, dietary
    restrictions, macro alignment.
    """

    def __init__(self) -> None:
        pass

    def rank(self, recipes: list[dict], profile: dict) -> list[dict]:
        """Return recipes unmodified. Real implementation re-orders by score."""
        return recipes
