"""Tests for query processing and rule-based NER."""

from __future__ import annotations

from parser.parser_pipeline import ParserPipeline
from parser.tokenizer import QueryTokenizer


def test_tokenizer_normalizes_and_expands_abbreviations() -> None:
    tokenizer = QueryTokenizer()
    assert tokenizer.normalize("  Flat  302,  Lotus Heights Rd.  BANER Pune  ") == "flat 302 lotus heights road baner pune"


def test_tokenizer_generates_phrase_combinations() -> None:
    tokenizer = QueryTokenizer()
    phrases = tokenizer.generate_phrases(["lotus", "heights", "baner", "pune"])
    assert "lotus heights" in phrases
    assert "heights baner" in phrases
    assert "baner pune" in phrases


def test_parser_pipeline_handles_full_address() -> None:
    pipeline = ParserPipeline()
    result = pipeline.parse("Flat 302 Lotus Heights Baner Pune 411045")
    assert result["intent"] == "FULL_ADDRESS_SEARCH"
    assert result["pincode"] == "411045"
    assert result["building_name"] == "Lotus Heights"
    assert result["locality"] == "Baner"
    assert result["city"] == "Pune"
    assert result["confidence"] > 0


def test_parser_pipeline_handles_only_pincode() -> None:
    pipeline = ParserPipeline()
    result = pipeline.parse("411045")
    assert result["intent"] == "PINCODE_SEARCH"
    assert result["pincode"] == "411045"


def test_parser_pipeline_handles_only_city_and_mixed_order_input() -> None:
    pipeline = ParserPipeline()
    city_result = pipeline.parse("Pune")
    mixed_result = pipeline.parse("Maharashtra Baner Pune Lotus Heights")
    assert city_result["intent"] == "CITY_SEARCH"
    assert mixed_result["state"] == "Maharashtra"
    assert mixed_result["city"] == "Pune"
