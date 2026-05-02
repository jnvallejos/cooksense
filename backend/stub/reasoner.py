"""Stub implementation of IngredientReasoner."""


class IngredientReasoner:
    """Naive ingredient reasoner: passes ingredients through unchanged.

    Real implementation in cooksense-core normalizes synonyms, infers quantities,
    detects missing categories, and applies dietary constraint filters.
    """

    def __init__(self) -> None:
        pass

    def reason(self, ingredients: list[str], profile: dict) -> list[str]:
        """Return ingredients unchanged. Real implementation normalizes and filters."""
        return ingredients
