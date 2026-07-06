"""Elasticsearch query builder for the search package."""

from __future__ import annotations

from typing import Any


class QueryBuilder:
    """Build Elasticsearch queries for normalized address search."""

    def __init__(self, config: dict[str, Any]) -> None:
        search_config = config.get("search", {})
        self.fuzzy_fuzziness = search_config.get("fuzzy_fuzziness", "AUTO")
        self.phrase_slop = int(search_config.get("phrase_slop", 2))
        self.autocomplete_min_chars = int(search_config.get("autocomplete_min_chars", 2))
        self.quality_score_boost = float(search_config.get("quality_score_boost", 0.05))
        self.source_fields = config.get("source_fields", [])

    def build_search_body(
        self,
        strategy: str,
        query: str | None = None,
        size: int = 20,
        filters: dict[str, str | None] | None = None,
        geo: dict[str, Any] | None = None,
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        filters = filters or {}
        geo = geo or {}
        parsed_entities = parsed_entities or {}

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
        body = builder(query=query, size=size, filters=filters, geo=geo, parsed_entities=parsed_entities)
        if self.source_fields:
            body["_source"] = self.source_fields
        return body

    def build_exact_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
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
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_fuzzy_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
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
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_phrase_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
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
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_autocomplete_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
        if query and len(query) >= self.autocomplete_min_chars:
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
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_hierarchical_admin_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
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
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_hierarchical_pincode_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
        if filters.get("city"):
            must.append({"match_phrase": {"city_name": filters["city"]}})
        if filters.get("state"):
            must.append({"match_phrase": {"state_name": filters["state"]}})
        if filters.get("pincode"):
            must.append({"term": {"pincode": filters["pincode"]}})
        elif query:
            must.append({"term": {"pincode": query}})
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_geospatial_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
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

        return self._build_function_score(must=must, should=should, filter_clauses=filter_clauses, size=size)

    def build_auto_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parsed_entities = parsed_entities or {}
        if geo.get("lat") is not None and geo.get("lon") is not None:
            return self.build_geospatial_query(query, size, filters, geo, parsed_entities)
        if filters.get("pincode") or parsed_entities.get("pincode"):
            return self.build_hierarchical_pincode_query(query, size, {**filters, "pincode": filters.get("pincode") or parsed_entities.get("pincode")}, geo, parsed_entities)
        if any(filters.get(key) for key in ("state", "district", "city", "locality", "building")):
            return self.build_hierarchical_admin_query(query, size, filters, geo, parsed_entities)
        if query and query.isdigit() and len(query) == 6:
            return self.build_exact_query(query, size, {**filters, "pincode": query}, geo, parsed_entities)
        if query and len(query.split()) >= 4:
            return self.build_phrase_query(query, size, filters, geo, parsed_entities)
        if query and len(query) <= 12:
            return self.build_autocomplete_query(query, size, filters, geo, parsed_entities)
        return self.build_fuzzy_query(query, size, filters, geo, parsed_entities)

    def _wrap_bool_query(
        self,
        must: list[dict[str, Any]],
        should: list[dict[str, Any]],
        filters: dict[str, str | None],
        geo: dict[str, Any],
        size: int,
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
        if should:
            bool_query["should"] = should
            bool_query["minimum_should_match"] = 1

        return self._build_function_score(
            must=bool_query.get("must", []),
            should=bool_query.get("should", []),
            filter_clauses=bool_query["filter"],
            size=size,
            minimum_should_match=bool_query.get("minimum_should_match"),
        )

    def _build_function_score(
        self,
        must: list[dict[str, Any]],
        should: list[dict[str, Any]],
        filter_clauses: list[dict[str, Any]],
        size: int,
        minimum_should_match: int | None = None,
    ) -> dict[str, Any]:
        bool_query: dict[str, Any] = {
            "must": must or [{"match_all": {}}],
            "filter": filter_clauses,
        }
        if should:
            bool_query["should"] = should
            bool_query["minimum_should_match"] = minimum_should_match or 1

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

    def _boost_clauses(self, parsed_entities: dict[str, Any]) -> list[dict[str, Any]]:
        clauses: list[dict[str, Any]] = []
        if parsed_entities.get("building_name"):
            clauses.append({"term": {"building_name.keyword": parsed_entities["building_name"]}})
            clauses.append({"match_phrase": {"building_name": parsed_entities["building_name"]}})
        if parsed_entities.get("locality"):
            clauses.append({"term": {"locality.keyword": parsed_entities["locality"]}})
        if parsed_entities.get("city"):
            clauses.append({"term": {"city_name.keyword": parsed_entities["city"]}})
        if parsed_entities.get("district"):
            clauses.append({"term": {"district_name.keyword": parsed_entities["district"]}})
        if parsed_entities.get("state"):
            clauses.append({"term": {"state_name.keyword": parsed_entities["state"]}})
        if parsed_entities.get("pincode"):
            clauses.append({"term": {"pincode": parsed_entities["pincode"]}})
        if parsed_entities.get("road_name"):
            clauses.append({"match_phrase": {"road_name": parsed_entities["road_name"]}})
        return clauses

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
