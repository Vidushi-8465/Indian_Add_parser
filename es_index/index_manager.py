"""Index creation with custom mappings and analyzers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch
from loguru import logger

from utils.constants import PROJECT_ROOT


def _resolve_synonyms_path(config: dict[str, Any]) -> Path:
    analysis = config.get("analysis", {})
    synonyms_file = analysis.get(
        "synonyms_file",
        "datasets/dictionaries/address_synonyms.txt",
    )

    path = Path(synonyms_file)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path


def _load_synonym_rules(config: dict[str, Any]) -> list[str]:
    """Load synonym rules from synonym file."""

    synonyms_path = _resolve_synonyms_path(config)

    if not synonyms_path.exists():
        return []

    rules = []

    for line in synonyms_path.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        rules.append(line.replace("\t", ", "))

    return rules


def _filter_chain(
    names: list[str],
    available_filters: dict[str, Any],
) -> list[str]:

    return [
        name
        for name in names
        if name in ("lowercase", "asciifolding")
        or name in available_filters
    ]


def build_index_settings(
    config: dict[str, Any],
) -> dict[str, Any]:

    analysis = config.get("analysis", {})
    index = config.get("index", {})

    synonym_rules = _load_synonym_rules(config)

    filters = {
        "address_edge_ngram": {
            "type": "edge_ngram",
            "min_gram": int(
                analysis.get("edge_ngram_min", 2)
            ),
            "max_gram": int(
                analysis.get("edge_ngram_max", 20)
            ),
        }
    }

    if synonym_rules:

        filters["address_synonyms"] = {
            "type": "synonym",
            "synonyms": synonym_rules,
            "expand": True,
            "lenient": True,
        }

    analyzers = {

        "address_analyzer": {

            "type": "custom",

            "tokenizer": "standard",

            "filter": _filter_chain(
                [
                    "lowercase",
                    "asciifolding",
                    "address_synonyms",
                ],
                filters,
            ),
        },

        "autocomplete_index": {

            "type": "custom",

            "tokenizer": "standard",

            "filter": _filter_chain(
                [
                    "lowercase",
                    "asciifolding",
                    "address_synonyms",
                    "address_edge_ngram",
                ],
                filters,
            ),
        },

        "autocomplete_search": {

            "type": "custom",

            "tokenizer": "standard",

            "filter": _filter_chain(
                [
                    "lowercase",
                    "asciifolding",
                    "address_synonyms",
                ],
                filters,
            ),
        },
    }

    return {

        "number_of_shards": index.get(
            "number_of_shards",
            3,
        ),

        "number_of_replicas": index.get(
            "number_of_replicas",
            0,
        ),

        "refresh_interval": index.get(
            "refresh_interval",
            "30s",
        ),

        "analysis": {
            "filter": filters,
            "analyzer": analyzers,
        },
    }


def build_index_mappings() -> dict[str, Any]:

    searchable = {

        "type": "text",

        "analyzer": "address_analyzer",

        "fields": {

            "keyword": {
                "type": "keyword",
                "ignore_above": 512,
            }
        },
    }

    autocomplete = {

        "type": "text",

        "analyzer": "autocomplete_index",

        "search_analyzer": "autocomplete_search",

        "fields": {

            "keyword": {
                "type": "keyword",
                "ignore_above": 512,
            }
        },
    }

    return {

        "properties": {

            "address_hash": {
                "type": "keyword"
            },

            "full_address": searchable,

            "searchable_text": searchable,

            "building_name": autocomplete,

            "road_name": searchable,

            "locality": autocomplete,

            "city_name": searchable,

            "district_name": searchable,

            "subdistrict_name": searchable,

            "state_name": searchable,

            "office_name": searchable,

            "region_name": searchable,

            "division_name": searchable,

            "circle_name": searchable,

            "pincode": {
                "type": "keyword"
            },

            "quality_score": {
                "type": "float"
            },

            "latitude": {
                "type": "float"
            },

            "longitude": {
                "type": "float"
            },

            "location": {

                "type": "geo_point",

                "ignore_malformed": True,
            },

            "source_file": {
                "type": "keyword"
            },

            "indexed_at": {
                "type": "date"
            },
        }
    }


class IndexManager:

    def __init__(
        self,
        client: Elasticsearch,
        config: dict[str, Any],
    ):

        self.client = client
        self.config = config

        self.index_name = config.get(
            "index",
            {},
        ).get(
            "name",
            "indian_addresses",
        )

        self.logger = logger.bind(
            module="es_index.index_manager"
        )

    def index_exists(self):

        return bool(
            self.client.indices.exists(
                index=self.index_name
            )
        )

    def create_index(
        self,
        recreate: bool = False,
    ):

        if recreate and self.index_exists():

            self.logger.warning(
                "Deleting existing index '{}'",
                self.index_name,
            )

            self.client.indices.delete(
                index=self.index_name
            )

        if self.index_exists():

            self.logger.info(
                "Index '{}' already exists",
                self.index_name,
            )

            return {
                "created": False,
                "index": self.index_name,
            }

        body = {

            "settings": build_index_settings(
                self.config
            ),

            "mappings": build_index_mappings(),
        }

        self.client.indices.create(
            index=self.index_name,
            body=body,
        )

        self.logger.success(
            "Created index '{}'",
            self.index_name,
        )

        return {

            "created": True,

            "index": self.index_name,
        }

    def get_index_stats(self):

        if not self.index_exists():

            return {
                "exists": False
            }

        stats = self.client.indices.stats(
            index=self.index_name
        )

        index_stats = stats["indices"][
            self.index_name
        ]

        docs = index_stats["total"]["docs"]

        store = index_stats["total"]["store"]

        return {

            "exists": True,

            "index": self.index_name,

            "document_count": docs["count"],

            "deleted_count": docs["deleted"],

            "store_size_bytes": store["size_in_bytes"],
        }

    def refresh_index(self):

        if self.index_exists():

            self.client.indices.refresh(
                index=self.index_name
            )