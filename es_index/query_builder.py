"""Elasticsearch query builders for address search."""

from __future__ import annotations

from typing import Any


class QueryBuilder:
    """Build Elasticsearch queries for multiple search modes."""

    INTENT_FIELDS: dict[str, list[str]] = {
        "pincode": [
            "pincode^18",
            "searchable_text^8",
            "full_address^6",
            "city_name^3",
            "district_name^2",
            "state_name^2",
        ],
        "city": [
            "city_name^14",
            "district_name^8",
            "state_name^4",
            "locality^5",
            "searchable_text^4",
            "full_address^3",
        ],
        "locality": [
            "locality^14",
            "building_name^7",
            "office_name^6",
            "city_name^5",
            "district_name^3",
            "searchable_text^4",
            "full_address^3",
        ],
        "building": [
            "building_name^16",
            "office_name^8",
            "locality^5",
            "city_name^4",
            "searchable_text^4",
            "full_address^3",
        ],
        "office": [
            "office_name^16",
            "building_name^8",
            "locality^5",
            "city_name^4",
            "searchable_text^4",
            "full_address^3",
        ],
        "full_address": [
            "full_address^16",
            "searchable_text^12",
            "building_name^5",
            "office_name^5",
            "locality^4",
            "city_name^3",
            "district_name^2",
            "state_name^2",
        ],
        "general": [
            "searchable_text^12",
            "full_address^10",
            "building_name^6",
            "office_name^6",
            "locality^5",
            "city_name^4",
            "district_name^3",
            "state_name^2",
            "pincode^6",
        ],
    }

    INTENT_PHRASE_FIELDS: dict[str, list[str]] = {
        "pincode": ["full_address", "searchable_text"],
        "city": ["city_name", "district_name", "full_address"],
        "locality": ["locality", "full_address", "searchable_text"],
        "building": ["building_name", "full_address", "searchable_text"],
        "office": ["office_name", "building_name", "full_address", "searchable_text"],
        "full_address": ["full_address", "searchable_text"],
        "general": ["full_address", "searchable_text"],
    }

    INTENT_FUZZY_FIELDS: list[str] = [
        "searchable_text^10",
        "full_address^9",
        "building_name^7",
        "office_name^7",
        "locality^6",
        "city_name^5",
        "district_name^4",
        "state_name^3",
        "pincode^6",
    ]

    FILTER_HINT_FIELDS: dict[str, str] = {
        "state": "state_name",
        "district": "district_name",
        "city": "city_name",
        "locality": "locality",
        "building": "building_name",
        "office": "office_name",
    }

    def __init__(self, config: dict[str, Any]) -> None:
        search_config = config.get("search", {})
        self.fuzzy_fuzziness = search_config.get("fuzzy_fuzziness", "AUTO")
        self.phrase_slop = int(search_config.get("phrase_slop", 2))
        self.quality_score_boost = float(search_config.get("quality_score_boost", 0.05))
        self.source_fields = config.get("source_fields", [])

    def build_search_body(
        self,
        strategy: str,
        query: str | None = None,
        size: int = 20,
        filters: dict[str, str | None] | None = None,
        geo: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        builders = {
            "exact": self.build_exact_query,
            "fuzzy": self.build_fuzzy_query,
            "phrase": self.build_phrase_query,
            "autocomplete": self.build_autocomplete_query,
            "hierarchical_admin": self.build_hierarchical_admin_query,
            "hierarchical_pincode": self.build_hierarchical_pincode_query,
            "geospatial": self.build_geospatial_query,
            "auto": self.build_auto_query,
        }
        builder = builders.get(strategy, self.build_auto_query)
        body = builder(query=query, size=size, filters=filters or {}, geo=geo or {})
        if self.source_fields:
            body["_source"] = self.source_fields
        return body

    def build_exact_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        return self._build_intent_aware_query(query=query, size=size, filters=filters, geo=geo, mode="exact")

    def build_fuzzy_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        return self._build_intent_aware_query(query=query, size=size, filters=filters, geo=geo, mode="fuzzy")

    def build_phrase_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        return self._build_intent_aware_query(query=query, size=size, filters=filters, geo=geo, mode="phrase")

    def build_autocomplete_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        return self._build_intent_aware_query(query=query, size=size, filters=filters, geo=geo, mode="autocomplete")

    def build_hierarchical_admin_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        """State → District → City → Locality → Building."""
        return self._build_intent_aware_query(query=query, size=size, filters=filters, geo=geo, mode="admin")

    def build_hierarchical_pincode_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        """Pincode → City → State."""
        return self._build_intent_aware_query(query=query, size=size, filters=filters, geo=geo, mode="pincode")

    def build_geospatial_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if query:
            must.append({"match": {"full_address": {"query": query}}})

        filter_clauses = self._filter_clauses(filters)
        if geo.get("lat") is not None and geo.get("lon") is not None:
            filter_clauses.append(
                {
                    "geo_distance": {
                        "distance": geo.get("distance", "5km"),
                        "location": {"lat": geo["lat"], "lon": geo["lon"]},
                    }
                }
            )

        body: dict[str, Any] = {
            "size": size,
            "query": {
                "function_score": {
                    "query": {"bool": {"must": must or [{"match_all": {}}], "filter": filter_clauses}},
                    "field_value_factor": {
                        "field": "quality_score",
                        "factor": self.quality_score_boost,
                        "missing": 0,
                    },
                    "boost_mode": "sum",
                }
            },
        }
        if geo.get("lat") is not None and geo.get("lon") is not None:
            body["sort"] = [
                {
                    "_geo_distance": {
                        "location": {"lat": geo["lat"], "lon": geo["lon"]},
                        "order": "asc",
                        "unit": "km",
                    }
                },
                "_score",
            ]
        return body

    def build_auto_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        if geo.get("lat") is not None and geo.get("lon") is not None:
            return self.build_geospatial_query(query, size, filters, geo)
        if filters.get("pincode"):
            return self.build_hierarchical_pincode_query(query, size, filters, geo)
        if any(filters.get(key) for key in ("state", "district", "city", "locality", "building", "office")):
            return self.build_hierarchical_admin_query(query, size, filters, geo)
        if query and query.isdigit() and len(query) == 6:
            filters = {**filters, "pincode": query}
            return self.build_exact_query(query, size, filters, geo)
        if query and len(query.split()) >= 4:
            return self.build_phrase_query(query, size, filters, geo)
        if query and len(query) <= 12:
            return self.build_autocomplete_query(query, size, filters, geo)
        return self.build_fuzzy_query(query, size, filters, geo)

    def _wrap_bool_query(
        self,
        must: list[dict[str, Any]],
        filters: dict[str, str | None],
        geo: dict[str, Any],
        size: int,
        minimum_should_match: int | None = None,
    ) -> dict[str, Any]:
        filter_clauses = self._filter_clauses(filters)
        if geo.get("lat") is not None and geo.get("lon") is not None:
            filter_clauses.append(
                {
                    "geo_distance": {
                        "distance": geo.get("distance", "5km"),
                        "location": {"lat": geo["lat"], "lon": geo["lon"]},
                    }
                }
            )

        bool_query: dict[str, Any] = {
            "must": must or [{"match_all": {}}],
            "filter": filter_clauses,
        }
        if minimum_should_match is not None:
            bool_query["should"] = must
            bool_query["minimum_should_match"] = minimum_should_match
            bool_query.pop("must", None)

        return {
            "size": size,
            "query": {
                "function_score": {
                    "query": {"bool": bool_query},
                    "field_value_factor": {
                        "field": "quality_score",
                        "factor": self.quality_score_boost,
                        "missing": 0,
                    },
                    "boost_mode": "sum",
                }
            },
        }

    @staticmethod
    def _filter_clauses(filters: dict[str, str | None]) -> list[dict[str, Any]]:
        mapping = {
            "state": "state_name.keyword",
            "district": "district_name.keyword",
            "city": "city_name.keyword",
            "locality": "locality.keyword",
            "pincode": "pincode",
            "building": "building_name.keyword",
            "office": "office_name.keyword",
        }
        clauses: list[dict[str, Any]] = []
        for key, field in mapping.items():
            value = filters.get(key)
            if value:
                clauses.append({"term": {field: value}})
        return clauses

    def _build_intent_aware_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        mode: str,
    ) -> dict[str, Any]:
        should_clauses: list[dict[str, Any]] = []
        if query:
            intent = self._detect_intent(query, filters, mode)
            should_clauses.extend(self._general_clauses(query))
            should_clauses.extend(self._intent_clauses(query, intent=intent, mode=mode))
        should_clauses.extend(self._boosted_filter_clauses(filters))

        filter_clauses = self._geo_clauses(geo)
        if should_clauses:
            bool_query: dict[str, Any] = {
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        else:
            bool_query = {"must": [{"match_all": {}}]}

        if filter_clauses:
            bool_query["filter"] = filter_clauses

        return {
            "size": size,
            "query": {
                "function_score": {
                    "query": {"bool": bool_query},
                    "field_value_factor": {
                        "field": "quality_score",
                        "factor": self.quality_score_boost,
                        "missing": 0,
                    },
                    "boost_mode": "sum",
                }
            },
        }

    def _general_clauses(self, query: str) -> list[dict[str, Any]]:
        return [
            self._multi_match_clause(
                query,
                fields=self.INTENT_FIELDS["general"],
                boost=5,
                tie_breaker=0.25,
            ),
            {
                "match_phrase": {
                    "searchable_text": {
                        "query": query,
                        "slop": self.phrase_slop,
                        "boost": 6,
                    }
                }
            },
            {
                "match_phrase": {
                    "full_address": {
                        "query": query,
                        "slop": self.phrase_slop,
                        "boost": 5,
                    }
                }
            },
            self._fuzzy_clause(query, boost=2),
        ]

    def _intent_clauses(self, query: str, intent: str, mode: str) -> list[dict[str, Any]]:
        fields = self.INTENT_FIELDS.get(intent, self.INTENT_FIELDS["general"])
        phrase_fields = self.INTENT_PHRASE_FIELDS.get(intent, self.INTENT_PHRASE_FIELDS["general"])
        clauses: list[dict[str, Any]] = []

        if mode == "exact":
            clauses.append(
                self._multi_match_clause(
                    query,
                    fields=fields,
                    boost=14,
                    match_type="phrase",
                    tie_breaker=0.2,
                )
            )
            clauses.extend(self._phrase_clauses(query, phrase_fields, boost=12))
            return clauses

        if mode == "phrase":
            clauses.extend(self._phrase_clauses(query, phrase_fields, boost=14))
            clauses.append(
                self._multi_match_clause(
                    query,
                    fields=fields,
                    boost=8,
                    tie_breaker=0.2,
                )
            )
            return clauses

        if mode == "autocomplete":
            clauses.append(
                self._multi_match_clause(
                    query,
                    fields=[
                        "searchable_text^10",
                        "full_address^8",
                        "building_name^8",
                        "office_name^8",
                        "locality^7",
                        "city_name^6",
                        "district_name^4",
                    ],
                    boost=8,
                    match_type="bool_prefix",
                )
            )
            clauses.extend(self._phrase_clauses(query, phrase_fields, boost=5))
            return clauses

        if mode == "pincode":
            clauses.append(
                {
                    "term": {
                        "pincode": {
                            "value": query,
                            "boost": 20,
                        }
                    }
                }
            )
            clauses.extend(self._phrase_clauses(query, ["full_address", "searchable_text"], boost=8))
            clauses.append(
                self._multi_match_clause(
                    query,
                    fields=fields,
                    boost=10,
                    tie_breaker=0.2,
                )
            )
            clauses.append(self._fuzzy_clause(query, boost=3))
            return clauses

        if mode == "admin":
            clauses.append(
                self._multi_match_clause(
                    query,
                    fields=[
                        "state_name^10",
                        "district_name^9",
                        "city_name^8",
                        "locality^6",
                        "building_name^4",
                        "office_name^4",
                        "searchable_text^4",
                        "full_address^3",
                    ],
                    boost=8,
                    tie_breaker=0.2,
                )
            )
            clauses.extend(self._phrase_clauses(query, ["state_name", "district_name", "city_name", "locality"], boost=7))
            clauses.append(self._fuzzy_clause(query, boost=4))
            return clauses

        clauses.append(
            self._multi_match_clause(
                query,
                fields=fields,
                boost=10,
                tie_breaker=0.25,
            )
        )
        clauses.extend(self._phrase_clauses(query, phrase_fields, boost=9))
        clauses.append(self._fuzzy_clause(query, boost=5))
        return clauses

    def _boosted_filter_clauses(self, filters: dict[str, str | None]) -> list[dict[str, Any]]:
        clauses: list[dict[str, Any]] = []
        for key, field in self.FILTER_HINT_FIELDS.items():
            value = filters.get(key)
            if not value:
                continue
            clauses.append(
                {
                    "match_phrase": {
                        field: {
                            "query": value,
                            "boost": 10 if key in {"city", "locality", "building", "office"} else 8,
                        }
                    }
                }
            )
        if filters.get("pincode"):
            clauses.append(
                {
                    "term": {
                        "pincode": {
                            "value": filters["pincode"],
                            "boost": 15,
                        }
                    }
                }
            )
        return clauses

    def _phrase_clauses(self, query: str, fields: list[str], boost: float) -> list[dict[str, Any]]:
        clauses: list[dict[str, Any]] = []
        for field in fields:
            clauses.append(
                {
                    "match_phrase": {
                        field: {
                            "query": query,
                            "slop": self.phrase_slop,
                            "boost": boost,
                        }
                    }
                }
            )
        return clauses

    def _multi_match_clause(
        self,
        query: str,
        fields: list[str],
        boost: float,
        match_type: str = "best_fields",
        tie_breaker: float | None = None,
    ) -> dict[str, Any]:
        clause: dict[str, Any] = {
            "multi_match": {
                "query": query,
                "type": match_type,
                "fields": fields,
                "boost": boost,
            }
        }
        if match_type == "best_fields":
            clause["multi_match"]["fuzziness"] = self.fuzzy_fuzziness
        if tie_breaker is not None:
            clause["multi_match"]["tie_breaker"] = tie_breaker
        return clause

    def _fuzzy_clause(self, query: str, boost: float) -> dict[str, Any]:
        return {
            "multi_match": {
                "query": query,
                "type": "best_fields",
                "fuzziness": self.fuzzy_fuzziness,
                "fields": self.INTENT_FUZZY_FIELDS,
                "boost": boost,
                "tie_breaker": 0.2,
            }
        }

    def _geo_clauses(self, geo: dict[str, Any]) -> list[dict[str, Any]]:
        if geo.get("lat") is None or geo.get("lon") is None:
            return []
        return [
            {
                "geo_distance": {
                    "distance": geo.get("distance", "5km"),
                    "location": {"lat": geo["lat"], "lon": geo["lon"]},
                }
            }
        ]

    def _detect_intent(self, query: str, filters: dict[str, str | None], mode: str) -> str:
        if mode in {"exact", "fuzzy", "phrase", "pincode", "admin"}:
            return self._mode_to_intent(mode, query)

        normalized = query.strip().lower()
        token_count = len(normalized.split())
        if query.isdigit() and len(query) == 6:
            return "pincode"
        if any(keyword in normalized for keyword in ("post office", "office", "branch")):
            return "office"
        if any(keyword in normalized for keyword in ("building", "tower", "complex", "apartment", "society", "block")):
            return "building"
        if filters.get("city"):
            return "city"
        if filters.get("locality"):
            return "locality"
        if filters.get("building"):
            return "building"
        if filters.get("office"):
            return "office"
        if token_count >= 4:
            return "full_address"
        if token_count == 1:
            return "city"
        if token_count == 2:
            return "locality"
        return "general"

    @staticmethod
    def _mode_to_intent(mode: str, query: str) -> str:
        if mode == "pincode" and query.isdigit() and len(query) == 6:
            return "pincode"
        if mode == "admin":
            return "city"
        if mode == "autocomplete":
            return "building"
        if mode == "phrase":
            return "full_address"
        if mode == "exact":
            if query.isdigit() and len(query) == 6:
                return "pincode"
            return "full_address"
        return "general"
