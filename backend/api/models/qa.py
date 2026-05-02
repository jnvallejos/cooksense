"""Conversational follow-up (`POST /api/recipes/{id}/ask`) request and response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PreviousQuestion(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class RecipeQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    previous_questions: list[PreviousQuestion] = Field(default_factory=list)


class RecipeAnswerResponse(BaseModel):
    answer: str
    from_cache: bool
    remaining_questions_today: int = Field(ge=0)
