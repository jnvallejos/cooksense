"""Tests for the QAResponder stub."""

from __future__ import annotations

from stub.qa_responder import QAResponder


def test_answer_returns_demo_english_by_default():
    responder = QAResponder()
    result = responder.answer(
        recipe={"id": "r1"},
        question="Can I substitute spinach?",
        previous_questions=[],
    )
    assert result == QAResponder.DEMO_EN


def test_answer_returns_demo_spanish_when_language_es():
    responder = QAResponder()
    result = responder.answer(
        recipe={"id": "r1"},
        question="¿Puedo cambiar la albahaca?",
        previous_questions=[],
        language="es",
    )
    assert result == QAResponder.DEMO_ES


def test_answer_ignores_previous_questions_in_stub():
    responder = QAResponder()
    long_history = [{"question": "q", "answer": "a"} for _ in range(20)]
    result = responder.answer(
        recipe={"id": "r1"},
        question="another?",
        previous_questions=long_history,
    )
    assert isinstance(result, str)


def test_answer_returns_str_for_unknown_language():
    responder = QAResponder()
    # Spec only requires en/es; falling back to demo English is fine.
    result = responder.answer(
        recipe={"id": "r1"},
        question="?",
        previous_questions=[],
        language="fr",
    )
    assert result == QAResponder.DEMO_EN
