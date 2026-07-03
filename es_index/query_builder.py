"""Elasticsearch query builders for address search."""

from __future__ import annotations

from typing import Any


class QueryBuilder:
    """Build Elasticsearch queries for multiple search modes."""

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
        must: list[dict[str, Any]] = []
        if query:
            must.append(
                {
                    "multi_match": {
                        "query": query,
                        "type": "phrase",
                        "fields": [
                            "full_address.phrase",
                            "building_name.keyword",
                            "locality.keyword",
                            "city_name.keyword",
                            "district_name.keyword",
                            "state_name.keyword",
                            "pincode",
                        ],
                    }
                }
            )
        return self._wrap_bool_query(must=must, filters=filters, geo=geo, size=size)

    def build_fuzzy_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if query:
            must.append(
                {
                    "multi_match": {
                        "query": query,
                        "type": "best_fields",
                        "fuzziness": self.fuzzy_fuzziness,
                        "fields": [
                            "full_address^4",
                            "building_name^3",
                            "locality^3",
                            "road_name^2",
                            "city_name^2",
                            "district_name",
                            "state_name",
                            "office_name",
                        ],
                    }
                }
            )
        return self._wrap_bool_query(must=must, filters=filters, geo=geo, size=size)

    def build_phrase_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if query:
            must.append(
                {
                    "match_phrase": {
                        "full_address": {
                            "query": query,
                            "slop": self.phrase_slop,
                        }
                    }
                }
            )
        return self._wrap_bool_query(must=must, filters=filters, geo=geo, size=size)

    def build_autocomplete_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if query:
            must.append(
                {
                    "multi_match": {
                        "query": query,
                        "type": "bool_prefix",
                        "fields": [
                            "building_name",
                            "locality",
                            "full_address",
                            "city_name",
                            "district_name",
                        ],
                    }
                }
            )
        return self._wrap_bool_query(must=must, filters=filters, geo=geo, size=size)

    def build_hierarchical_admin_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        """State → District → City → Locality → Building."""
        must: list[dict[str, Any]] = []
        if filters.get("building") or query:
            must.append(
                {
                    "multi_match": {
                        "query": filters.get("building") or query or "",
                        "fields": ["building_name^3", "office_name^2", "road_name", "full_address"],
                    }
                }
            )
        if filters.get("locality"):
            must.append({"match_phrase": {"locality": filters["locality"]}})
        return self._wrap_bool_query(must=must, filters=filters, geo=geo, size=size)

    def build_hierarchical_pincode_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
    ) -> dict[str, Any]:
        """Pincode → City → State."""
        must: list[dict[str, Any]] = []
        if filters.get("city"):
            must.append({"match_phrase": {"city_name": filters["city"]}})
        if filters.get("state"):
            must.append({"match_phrase": {"state_name": filters["state"]}})
        if query and not filters.get("pincode"):
            must.append({"multi_match": {"query": query, "fields": ["full_address", "locality", "building_name"]}})
        return self._wrap_bool_query(must=must, filters=filters, geo=geo, size=size)

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
        if any(filters.get(key) for key in ("state", "district", "city", "locality", "building")):
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
        }
        clauses: list[dict[str, Any]] = []
        for key, field in mapping.items():
            value = filters.get(key)
            if value:
                clauses.append({"term": {field: value}})
        return clauses
