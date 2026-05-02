"""Vision endpoint request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DetectedIngredient(BaseModel):
    name: str
    name_es: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_quantity: str
    category: str


class VisionExtractResponse(BaseModel):
    ingredients: list[DetectedIngredient]
    image_hash: str
    from_cache: bool
    remaining_calls_today: int = Field(ge=0)
