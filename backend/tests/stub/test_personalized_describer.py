"""Tests for the PersonalizedDescriber stub."""

from __future__ import annotations

from stub.personalized_describer import PersonalizedDescriber


def test_describe_returns_english_for_english_profile():
    describer = PersonalizedDescriber()
    result = describer.describe(recipe={"id": "r1"}, profile={"language": "en"})
    assert result == PersonalizedDescriber.GENERIC_EN


def test_describe_returns_spanish_for_spanish_profile():
    describer = PersonalizedDescriber()
    result = describer.describe(recipe={"id": "r1"}, profile={"language": "es"})
    assert result == PersonalizedDescriber.GENERIC_ES


def test_describe_defaults_to_english_when_language_missing():
    describer = PersonalizedDescriber()
    result = describer.describe(recipe={"id": "r1"}, profile={})
    assert result == PersonalizedDescriber.GENERIC_EN


def test_describe_returns_str_type():
    describer = PersonalizedDescriber()
    assert isinstance(describer.describe({}, {"language": "en"}), str)
