"""Stub implementation of ShoppingListBuilder.

Returns the input ingredients verbatim with `estimated_quantity="some"` and
`category="other"` for every entry. Identity translation (no language-specific
mapping). Real implementation in `cooksense-core` consolidates plus runs ONE
Haiku call for quantity inference and ES translations.
"""

from __future__ import annotations


class ShoppingListBuilder:
    """Stub: identity-style shopping list with generic quantities."""

    def __init__(
        self,
        client: object | None = None,
        reasoner: object | None = None,
        model: str = "stub",
    ) -> None:
        self.client = client
        self.reasoner = reasoner
        self.model = model

    def build(
        self,
        ingredients_with_attribution: dict[str, list[str]],
        profile: dict,
        max_tokens: int = 1024,
    ) -> list[dict]:
        return [
            {
                "ingredient": name,
                "ingredient_es": name,
                "estimated_quantity": "some",
                "category": "other",
                "needed_for": list(recipe_ids),
            }
            for name, recipe_ids in ingredients_with_attribution.items()
        ]
