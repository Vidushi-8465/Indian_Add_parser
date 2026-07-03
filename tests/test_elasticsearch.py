"""Tests for Elasticsearch indexing and search."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from es_index.bulk_indexer import BulkIndexer
from es_index.document_mapper import DocumentMapper
from es_index.index_manager import IndexManager, build_index_mappings, build_index_settings
from es_index.query_builder import QueryBuilder
from es_index.search_service import SearchService
from utils.file_utils import load_yaml_config


@pytest.fixture
def es_config() -> dict:
    return load_yaml_config(Path(__file__).resolve().parent.parent / "configs" / "elasticsearch.yaml")


def test_index_settings_include_custom_analyzers(es_config: dict) -> None:
    settings = build_index_settings(es_config)
    analyzers = settings["analysis"]["analyzer"]
    assert "address_analyzer" in analyzers
    assert "autocomplete_index" in analyzers
    assert "autocomplete_search" in analyzers


def test_index_mappings_include_geo_point_and_keywords() -> None:
    mappings = build_index_mappings()
    properties = mappings["properties"]
    assert properties["location"]["type"] == "geo_point"
    assert properties["pincode"]["type"] == "keyword"
    assert properties["full_address"]["fields"]["keyword"]["type"] == "keyword"


def test_document_mapper_builds_geo_point_and_id() -> None:
    mapper = DocumentMapper(id_field="address_hash")
    row = pd.Series(
        {
            "address_hash": "abc123",
            "full_address": "TCS, Hinjewadi, Pune, Maharashtra, 411057",
            "building_name": "TCS",
            "locality": "Hinjewadi",
            "city_name": "Pune",
            "state_name": "Maharashtra",
            "pincode": "411057",
            "latitude": "18.59",
            "longitude": "73.73",
            "quality_score": "68.75",
        }
    )
    document_id, document = mapper.map_row(row, row_number=1)
    assert document_id == "abc123"
    assert document["location"] == {"lat": 18.59, "lon": 73.73}
    assert document["quality_score"] == 68.75


def test_document_mapper_skips_empty_rows() -> None:
    mapper = DocumentMapper()
    row = pd.Series({"building_name": None, "locality": None, "pincode": None})
    assert mapper.map_row(row, row_number=5) is None


def test_query_builder_exact_fuzzy_phrase_autocomplete(es_config: dict) -> None:
    builder = QueryBuilder(es_config)

    exact = builder.build_search_body("exact", query="411057", size=5)
    fuzzy = builder.build_search_body("fuzzy", query="Hinjewadi Pune", size=5)
    phrase = builder.build_search_body("phrase", query="Rajiv Gandhi Infotech Park", size=5)
    autocomplete = builder.build_search_body("autocomplete", query="Hinj", size=5)

    assert exact["query"]["function_score"]["query"]["bool"]["must"]
    assert fuzzy["query"]["function_score"]["query"]["bool"]["must"][0]["multi_match"]["fuzziness"] == "AUTO"
    assert phrase["query"]["function_score"]["query"]["bool"]["must"][0]["match_phrase"]["full_address"]["query"]
    assert autocomplete["query"]["function_score"]["query"]["bool"]["must"][0]["multi_match"]["type"] == "bool_prefix"


def test_query_builder_hierarchical_admin_filters(es_config: dict) -> None:
    builder = QueryBuilder(es_config)
    body = builder.build_search_body(
        "hierarchical_admin",
        query="TCS",
        size=10,
        filters={
            "state": "Maharashtra",
            "district": "Pune",
            "city": "Pune",
            "locality": "Hinjewadi",
            "building": "TCS",
        },
    )
    filters = body["query"]["function_score"]["query"]["bool"]["filter"]
    assert any("state_name.keyword" in clause.get("term", {}) for clause in filters)


def test_query_builder_hierarchical_pincode_filters(es_config: dict) -> None:
    builder = QueryBuilder(es_config)
    body = builder.build_search_body(
        "hierarchical_pincode",
        query=None,
        size=10,
        filters={"pincode": "411057", "city": "Pune", "state": "Maharashtra"},
    )
    filters = body["query"]["function_score"]["query"]["bool"]["filter"]
    assert any("pincode" in clause for clause in filters)


def test_query_builder_geospatial_includes_geo_distance(es_config: dict) -> None:
    builder = QueryBuilder(es_config)
    body = builder.build_search_body(
        "geospatial",
        query="TCS",
        size=10,
        geo={"lat": 18.59, "lon": 73.73, "distance": "3km"},
    )
    filter_clauses = body["query"]["function_score"]["query"]["bool"]["filter"]
    assert any("geo_distance" in clause for clause in filter_clauses)
    assert body["sort"][0]["_geo_distance"]["order"] == "asc"


def test_index_manager_create_index(es_config: dict) -> None:
    client = MagicMock()
    client.indices.exists.return_value = False
    manager = IndexManager(client, es_config)
    result = manager.create_index()
    assert result["created"] is True
    client.indices.create.assert_called_once()


def test_bulk_indexer_batches_with_retry(es_config: dict) -> None:
    client = MagicMock()
    indexer = BulkIndexer(client, index_name="indian_addresses", batch_size=2, max_retries=2)

    actions = [
        {"_id": "1", "_source": {"full_address": "A"}},
        {"_id": "2", "_source": {"full_address": "B"}},
        {"_id": "3", "_source": {"full_address": "C"}},
    ]

    with patch("es_index.bulk_indexer.bulk", side_effect=[(2, []), (1, [])]) as mock_bulk:
        stats = indexer.index_actions(actions)

    assert mock_bulk.call_count == 2
    assert stats.batches == 2
    assert stats.indexed == 3


def test_search_service_returns_candidates(es_config: dict) -> None:
    client = MagicMock()
    client.search.return_value = {
        "took": 12,
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_id": "abc123",
                    "_score": 4.2,
                    "_source": {
                        "address_hash": "abc123",
                        "full_address": "TCS, Hinjewadi, Pune, Maharashtra, 411057",
                        "building_name": "TCS",
                        "locality": "Hinjewadi",
                        "city_name": "Pune",
                        "district_name": "Pune",
                        "state_name": "Maharashtra",
                        "pincode": "411057",
                        "quality_score": 68.75,
                    },
                }
            ],
        },
    }

    service = SearchService(client, es_config)
    with patch.object(service.search_logger, "log_search"):
        result = service.search(query="TCS Hinjewadi", strategy="fuzzy", size=5)

    assert result["strategy"] == "fuzzy"
    assert result["total_hits"] == 1
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["building_name"] == "TCS"
    client.search.assert_called_once()
