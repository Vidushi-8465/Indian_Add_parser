"""Tests for the standalone search package."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from search.entity_detector import EntityDetector
from search.query_builder import QueryBuilder
from search.query_normalizer import QueryNormalizer
from search.query_parser import QueryParser
from search.search_service import SearchService
from utils.file_utils import load_yaml_config


def test_query_normalizer_expands_abbreviations() -> None:
    normalizer = QueryNormalizer()
    assert normalizer.normalize_query("Flat 302 Lotus Heights Baner Pune Rd.") == "flat 302 lotus heights baner pune road"


def test_query_parser_detects_full_address_intent() -> None:
    parser = QueryParser()
    result = parser.parse("Flat 302 Lotus Heights Baner Pune 411045")
    assert result.intent == "FULL_ADDRESS_SEARCH"
    assert "lotus heights" in result.phrases
    assert result.validation_errors == []


def test_entity_detector_extracts_core_fields() -> None:
    detector = EntityDetector()
    entities = detector.detect("Flat 302 Lotus Heights Baner Pune 411045", ["flat", "302", "lotus", "heights", "baner", "pune", "411045"])
    assert entities.pincode == "411045"
    assert entities.building_name == "Lotus Heights"
    assert entities.locality == "Baner"
    assert entities.city == "Pune"


def test_query_builder_builds_search_body() -> None:
    config = load_yaml_config(Path(__file__).resolve().parent.parent / "configs" / "elasticsearch.yaml")
    builder = QueryBuilder(config)
    body = builder.build_search_body(
        "auto",
        query="lotus heights baner pune",
        size=5,
        parsed_entities={"building_name": "Lotus Heights", "locality": "Baner", "city": "Pune"},
    )
    assert body["size"] == 5
    assert body["query"]["function_score"]["query"]["bool"]["should"]


def test_search_service_returns_preview_and_reranks_hits() -> None:
    config = load_yaml_config(Path(__file__).resolve().parent.parent / "configs" / "elasticsearch.yaml")
    client = MagicMock()
    client.search.return_value = {
        "took": 10,
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_id": "abc123",
                    "_score": 4.2,
                    "_source": {
                        "address_hash": "abc123",
                        "full_address": "Lotus Heights, Baner, Pune, Maharashtra, 411045",
                        "building_name": "Lotus Heights",
                        "locality": "Baner",
                        "city_name": "Pune",
                        "district_name": "Pune",
                        "state_name": "Maharashtra",
                        "pincode": "411045",
                        "quality_score": 72.0,
                    },
                }
            ],
        },
    }

    service = SearchService(client, config)
    preview = service.preview(query="Lotus Heights Baner Pune 411045")
    assert preview["analysis"]["intent"] == "FULL_ADDRESS_SEARCH"
    assert preview["size"] == 20

    result = service.search(query="Lotus Heights Baner Pune 411045")
    assert result["total_hits"] == 1
    assert result["results"][0]["building_name"] == "Lotus Heights"
    assert result["results"][0]["confidence"] > 0
    assert result["retrieved_candidates"][0]["building_name"] == "Lotus Heights"
    client.search.assert_called_once()
    assert client.search.call_args.kwargs["body"]["size"] == 100
