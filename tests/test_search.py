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
    assert entities.flat_number == "302"
    assert entities.locality == "Baner"
    assert entities.city == "Pune"


def test_query_normalizer_corrects_spelling() -> None:
    normalizer = QueryNormalizer()
    assert normalizer.normalize_query("Banglore Maharastra") == "bangalore maharashtra"
    assert normalizer.normalize_query("appartment nr park") == "apartment near park"


def test_query_normalizer_number_helpers() -> None:
    normalizer = QueryNormalizer()
    assert normalizer.extract_numbers("flat 302 pune 411045") == ["302", "411045"]
    assert normalizer.has_potential_pincode("baner pune 411045") is True
    assert normalizer.has_potential_pincode("flat 302") is False


def test_entity_detector_extracts_office_name() -> None:
    detector = EntityDetector()
    entities = detector.detect(
        "Reliance Corporate Office Bandra Mumbai",
        ["reliance", "corporate", "office", "bandra", "mumbai"],
    )
    assert entities.office_name == "Reliance Corporate Office"
    assert entities.city == "Mumbai"


def test_entity_detector_extracts_landmark() -> None:
    detector = EntityDetector()
    entities = detector.detect(
        "near lotus temple delhi",
        ["near", "lotus", "temple", "delhi"],
    )
    assert entities.landmark == "Lotus Temple"
    assert entities.city == "Delhi"


def test_query_parser_detects_office_and_nearby_intents() -> None:
    parser = QueryParser()
    assert parser.parse("Reliance Corporate Office Bandra Mumbai").intent == "OFFICE_SEARCH"
    assert parser.parse("near lotus temple delhi").intent == "NEARBY_SEARCH"


def test_retrieve_candidates_deduplicates_by_hash() -> None:
    hits = [
        {"_id": "1", "_score": 9.0, "_source": {"address_hash": "h1", "full_address": "A"}},
        {"_id": "2", "_score": 8.0, "_source": {"address_hash": "h1", "full_address": "A"}},
        {"_id": "3", "_score": 7.0, "_source": {"address_hash": "h2", "full_address": "B"}},
    ]
    candidates = SearchService._retrieve_candidates(hits)
    assert [candidate.id for candidate in candidates] == ["1", "3"]
    assert candidates[0].retrieval_position == 1
    assert candidates[1].retrieval_position == 2


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


def test_query_builder_uses_city_and_pincode_intents() -> None:
    config = load_yaml_config(Path(__file__).resolve().parent.parent / "configs" / "elasticsearch.yaml")
    builder = QueryBuilder(config)

    city_body = builder.build_search_body("city", query="pune", size=5, parsed_entities={"city": "Pune"})
    city_must = city_body["query"]["function_score"]["query"]["bool"]["must"]
    assert any("multi_match" in clause for clause in city_must)

    pincode_body = builder.build_search_body("pincode", query="411045", size=5, parsed_entities={"pincode": "411045"})
    pincode_must = pincode_body["query"]["function_score"]["query"]["bool"]["must"]
    assert any(clause.get("term", {}).get("pincode") == "411045" for clause in pincode_must)


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
