"""User profile request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    cooking_for: str = Field(pattern="^(self|couple|family)$")
    household_size: int = Field(ge=1, le=20)
    dietary_restrictions: list[str] = Field(default_factory=list)
    fitness_goal: str = Field(pattern="^(none|lose|build|eat_better)$")
    cooking_skill: str = Field(pattern="^(beginner|intermediate|pro)$")
    time_budget_minutes: int = Field(ge=15, le=180)
    language: str = Field(pattern="^(en|es)$", default="en")


class ProfileResponse(BaseModel):
    user_id: str
    cooking_for: str
    household_size: int
    dietary_restrictions: list[str]
    fitness_goal: str
    cooking_skill: str
    time_budget_minutes: int
    language: str
    created_at: datetime
    updated_at: datetime
