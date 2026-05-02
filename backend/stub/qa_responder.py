"""Stub implementation of QAResponder.

Returns a bilingual demo answer regardless of the recipe, question, or
conversation history. The real implementation in `cooksense-core` composes a
multi-turn Anthropic call.
"""

from __future__ import annotations


class QAResponder:
    """Stub: returns a bilingual demo answer."""

    DEMO_EN = "This is a demo answer. Connect cooksense-core for real responses."
    DEMO_ES = (
        "Esta es una respuesta de demostración. Conectá cooksense-core para respuestas reales."
    )

    def __init__(self, client: object | None = None, model: str = "stub") -> None:
        self.client = client
        self.model = model

    def answer(
        self,
        recipe: dict,
        question: str,
        previous_questions: list[dict],
        language: str = "en",
        max_tokens: int = 1024,
    ) -> str:
        return self.DEMO_ES if language == "es" else self.DEMO_EN
