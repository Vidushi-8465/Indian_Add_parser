"""Index creation with custom mappings and analyzers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch
from loguru import logger

from utils.constants import PROJECT_ROOT


def _resolve_synonyms_path(config: dict[str, Any]) -> Path:
    analysis = config.get("analysis", {})
    synonyms_file = analysis.get("synonyms_file", "datasets/dictionaries/address_synonyms.txt")
    path = Path(synonyms_file)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _load_synonym_rules(config: dict[str, Any]) -> list[str]:
    """Load synonym rules from file for inline ES synonym filter."""
    synonyms_path = _resolve_synonyms_path(config)
    if not synonyms_path.exists():
        return []

    rules: list[str] = []
    for line in synonyms_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        rules.append(text.replace("\t", ", "))
    return rules


def build_index_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Return index settings including custom analyzers for Indian addresses."""
    index_config = config.get("index", {})
    analysis_config = config.get("analysis", {})
    synonym_rules = _load_synonym_rules(config)

    filters: dict[str, Any] = {
        "address_edge_ngram": {
            "type": "edge_ngram",
            "min_gram": int(analysis_config.get("edge_ngram_min", 2)),
            "max_gram": int(analysis_config.get("edge_ngram_max", 20)),
        },
        "address_word_delimiter": {
            "type": "word_delimiter_graph",
            "generate_word_parts": True,
            "split_on_case_change": True,
        },
    }

    if synonym_rules:
        filters["address_synonyms"] = {
            "type": "synonym",
            "synonyms": synonym_rules,
            "expand": True,
            "lenient": True,
        }

    analyzers: dict[str, Any] = {
        "address_analyzer": {
            "type": "custom",
            "tokenizer": "standard",
            "filter": _filter_chain(["lowercase", "asciifolding", "address_synonyms", "address_word_delimiter"], filters),
        },
        "autocomplete_index": {
            "type": "custom",
            "tokenizer": "standard",
            "filter": _filter_chain(["lowercase", "asciifolding", "address_synonyms", "address_edge_ngram"], filters),
        },
        "autocomplete_search": {
            "type": "custom",
            "tokenizer": "standard",
            "filter": _filter_chain(["lowercase", "asciifolding", "address_synonyms"], filters),
        },
    }

    return {
        "number_of_shards": index_config.get("number_of_shards", 3),
        "number_of_replicas": index_config.get("number_of_replicas", 0),
        "refresh_interval": index_config.get("refresh_interval", "30s"),
        "analysis": {
            "filter": filters,
            "analyzer": analyzers,
        },
    }


def _filter_chain(names: list[str], available_filters: dict[str, Any]) -> list[str]:
    """Include only filters that were actually registered."""
    return [name for name in names if name in ("lowercase", "asciifolding") or name in available_filters]


def build_index_mappings() -> dict[str, Any]:
    """Return field mappings for the indian_addresses index."""
    text_with_keyword = {
        "type": "text",
        "analyzer": "address_analyzer",
        "fields": {
            "keyword": {"type": "keyword", "ignore_above": 256},
            "phrase": {"type": "text", "analyzer": "address_analyzer"},
        },
    }
    autocomplete_field = {
        "type": "text",
        "analyzer": "autocomplete_index",
        "search_analyzer": "autocomplete_search",
        "fields": {
            "keyword": {"type": "keyword", "ignore_above": 256},
        },
    }

    return {
        "properties": {
            "address_hash": {"type": "keyword"},
            "full_address": text_with_keyword,
            "searchable_text": text_with_keyword,
            "building_name": autocomplete_field,
            "road_name": text_with_keyword,
            "locality": autocomplete_field,
            "city_name": text_with_keyword,
            "district_name": text_with_keyword,
            "subdistrict_name": text_with_keyword,
            "state_name": text_with_keyword,
            "pincode": {"type": "keyword"},
            "office_name": text_with_keyword,
            "latitude": {"type": "keyword"},
            "longitude": {"type": "keyword"},
            "location": {"type": "geo_point"},
            "quality_score": {"type": "float"},
            "source_file": {"type": "keyword"},
            "indexed_at": {"type": "date"},
        }
    }


class IndexManager:
    """Create and manage the indian_addresses Elasticsearch index."""

    def __init__(self, client: Elasticsearch, config: dict[str, Any]) -> None:
        self.client = client
        self.config = config
        self.index_name = config.get("index", {}).get("name", "indian_addresses")
        self.logger = logger.bind(module="es_index.index_manager")

    def index_exists(self) -> bool:
        return bool(self.client.indices.exists(index=self.index_name))

    def create_index(self, recreate: bool = False) -> dict[str, Any]:
        """Create the index with custom analyzers and mappings."""
        if recreate and self.index_exists():
            self.logger.warning("Deleting existing index '{}'", self.index_name)
            self.client.indices.delete(index=self.index_name)

        if self.index_exists():
            self.logger.info("Index '{}' already exists", self.index_name)
            return {"created": False, "index": self.index_name}

        body = {
            "settings": build_index_settings(self.config),
            "mappings": build_index_mappings(),
        }
        self.client.indices.create(index=self.index_name, **body)
        self.logger.info("Created index '{}' with custom mapping and analyzers", self.index_name)
        return {"created": True, "index": self.index_name}

    def get_index_stats(self) -> dict[str, Any]:
        if not self.index_exists():
            return {"exists": False, "index": self.index_name}

        stats = self.client.indices.stats(index=self.index_name)
        index_stats = stats.get("indices", {}).get(self.index_name, {})
        docs = index_stats.get("total", {}).get("docs", {})
        store = index_stats.get("total", {}).get("store", {})
        return {
            "exists": True,
            "index": self.index_name,
            "document_count": docs.get("count", 0),
            "deleted_count": docs.get("deleted", 0),
            "store_size_bytes": store.get("size_in_bytes", 0),
        }

    def refresh_index(self) -> None:
        if self.index_exists():
            self.client.indices.refresh(index=self.index_name)
