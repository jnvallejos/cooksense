"""Stub implementation of VisionExtractor.

Returns five generic ingredients regardless of input, in both EN and ES, so the
public demo runs end-to-end with no Anthropic credentials. The real
implementation in `cooksense-core` calls Claude Vision.
"""

from __future__ import annotations


_DEMO_INGREDIENTS: list[dict] = [
    {
        "name": "tomato",
        "name_es": "tomate",
        "confidence": 0.9,
        "estimated_quantity": "3 medium",
        "category": "vegetable",
    },
    {
        "name": "onion",
        "name_es": "cebolla",
        "confidence": 0.85,
        "estimated_quantity": "2",
        "category": "vegetable",
    },
    {
        "name": "garlic",
        "name_es": "ajo",
        "confidence": 0.8,
        "estimated_quantity": "4 cloves",
        "category": "vegetable",
    },
    {
        "name": "olive oil",
        "name_es": "aceite de oliva",
        "confidence": 0.95,
        "estimated_quantity": "1 cup",
        "category": "fat",
    },
    {
        "name": "salt",
        "name_es": "sal",
        "confidence": 0.7,
        "estimated_quantity": "to taste",
        "category": "seasoning",
    },
]


class VisionExtractor:
    """Stub: returns 5 generic ingredients regardless of image content."""

    def __init__(self, client: object | None = None, model: str = "stub") -> None:
        self.client = client
        self.model = model

    def extract(
        self,
        image_bytes: bytes,
        language: str = "en",
        max_tokens: int = 2048,
    ) -> list[dict]:
        # Return a fresh copy so callers can mutate without polluting the constant.
        return [dict(item) for item in _DEMO_INGREDIENTS]
