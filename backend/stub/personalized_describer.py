"""Stub implementation of PersonalizedDescriber.

Returns a generic, language-aware sentence regardless of recipe or profile so
the public demo can render personalized cards without any Anthropic call.
"""

from __future__ import annotations


class PersonalizedDescriber:
    """Stub: returns a generic description in profile language."""

    GENERIC_EN = "A simple recipe that matches your preferences."
    GENERIC_ES = "Una receta sencilla que coincide con tus preferencias."

    def __init__(self, client: object | None = None, model: str = "stub") -> None:
        self.client = client
        self.model = model

    def describe(
        self,
        recipe: dict,
        profile: dict,
        max_tokens: int = 512,
    ) -> str:
        return self.GENERIC_ES if profile.get("language") == "es" else self.GENERIC_EN
