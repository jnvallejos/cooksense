"""Tests for the VisionExtractor stub."""

from __future__ import annotations

from stub.vision_extractor import VisionExtractor


def test_extract_returns_five_ingredients():
    extractor = VisionExtractor()
    result = extractor.extract(image_bytes=b"\xff\xd8")
    assert len(result) == 5


def test_extract_each_ingredient_has_required_keys():
    extractor = VisionExtractor()
    result = extractor.extract(image_bytes=b"\xff\xd8")
    required = {"name", "name_es", "confidence", "estimated_quantity", "category"}
    for item in result:
        assert required <= item.keys()


def test_extract_returns_independent_dicts():
    extractor = VisionExtractor()
    first = extractor.extract(image_bytes=b"")
    second = extractor.extract(image_bytes=b"")
    first[0]["name"] = "mutated"
    assert second[0]["name"] != "mutated"


def test_extract_accepts_optional_kwargs():
    extractor = VisionExtractor(client=object(), model="stub-vision")
    result = extractor.extract(image_bytes=b"", language="es", max_tokens=4096)
    assert isinstance(result, list)
