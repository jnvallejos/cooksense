"""Stub implementation of IngredientReasoner.

Phase 0 introduced the legacy `reason(ingredients, profile)` method, which
must keep returning the input untouched (callers in older code rely on that).
Phase 2 adds `normalize(detected, language)` to match the real interface used
by the vision pipeline. The stub's normalize fills in `category="other"` when
missing and otherwise leaves the items alone.
"""

from __future__ import annotations


class IngredientReasoner:
    """Naive ingredient reasoner.

    Real implementation in `cooksense-core` normalizes synonyms, singularizes
    plurals, and infers categories from a curated lookup table.
    """

    def __init__(self) -> None:
        pass

    def reason(self, ingredients: list[str], profile: dict) -> list[str]:
        """Legacy Phase 0 stub: return ingredients unchanged."""
        return ingredients

    def normalize(
        self,
        detected: list[dict],
        language: str = "en",
    ) -> list[dict]:
        """Return a fresh list with `category` defaulted to 'other' when missing.

        The stub does not touch synonyms or plurals — that's the real
        reasoner's job. Input is not mutated.
        """
        return [
            {**item, "category": item.get("category") or "other"} for item in detected
        ]
