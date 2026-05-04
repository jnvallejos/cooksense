"""Shopping list endpoint response models."""

from __future__ import annotations

from pydantic import BaseModel


class ShoppingItem(BaseModel):
    ingredient: str
    ingredient_es: str | None = None
    estimated_quantity: str
    category: str
    needed_for: list[str]


class ShoppingListResponse(BaseModel):
    plan_id: str
    items: list[ShoppingItem]
    total_items: int
    language: str
