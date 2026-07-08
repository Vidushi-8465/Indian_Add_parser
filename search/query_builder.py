"""Elasticsearch query builder for the search package."""

from __future__ import annotations

from typing import Any


class QueryBuilder:
    """Build Elasticsearch queries for normalized address search."""

    BOOSTED_SEARCH_FIELDS = [
        "building_name^5",
        "office_name^4",
        "road_name^3",
        "locality^2",
        "city_name^1.5",
        "district_name^1.25",
        "state_name^1",
        "full_address^2",
    ]

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
            "city": self.build_city_query,
            "locality": self.build_locality_query,
            "district": self.build_district_query,
            "state": self.build_state_query,
            "building": self.build_building_query,
            "road": self.build_road_query,
            "full_address": self.build_full_address_query,
            "pincode": self.build_pincode_query,
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
            must.append(self._multi_match_clause(query, self.BOOSTED_SEARCH_FIELDS, query_type="phrase"))
        must.extend(self._location_match_clauses(filters, prefer_phrase=True, include_pincode=True))
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
                self._multi_match_clause(
                    query,
                    [
                        "building_name^5",
                        "office_name^4",
                        "road_name^3",
                        "locality^2",
                        "city_name^1.5",
                        "district_name^1.25",
                        "state_name^1",
                        "full_address^2",
                    ],
                    fuzziness=self.fuzzy_fuzziness,
                )
            )
        must.extend(self._location_match_clauses(filters, include_pincode=True))
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
            must.append(self._match_phrase_clause("full_address", query))
        must.extend(self._location_match_clauses(filters, prefer_phrase=True, include_pincode=True))
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
                self._multi_match_clause(
                    query,
                    ["building_name^4", "road_name^3", "locality^2", "city_name^1.5", "district_name^1.25", "full_address^2"],
                    query_type="bool_prefix",
                )
            )
        must.extend(self._location_match_clauses(filters, include_pincode=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_city_query(
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
            must.append(self._multi_match_clause(query, ["city_name^5", "locality^3", "district_name^2", "state_name^1.5", "full_address^1.5"]))
        must.extend(self._location_match_clauses(filters, include_city=True, include_locality=True, include_district=True, include_state=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_locality_query(
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
            must.append(self._multi_match_clause(query, ["locality^5", "road_name^4", "building_name^3", "city_name^2", "district_name^1.5", "state_name^1", "full_address^2"]))
        must.extend(self._location_match_clauses(filters, include_city=True, include_locality=True, include_district=True, include_state=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_district_query(
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
            must.append(self._multi_match_clause(query, ["district_name^5", "city_name^3", "locality^2", "state_name^2", "full_address^1.5"]))
        must.extend(self._location_match_clauses(filters, include_district=True, include_city=True, include_locality=True, include_state=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_state_query(
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
            must.append(self._multi_match_clause(query, ["state_name^5", "district_name^3", "city_name^2", "locality^1.5", "full_address^1.5"]))
        must.extend(self._location_match_clauses(filters, include_state=True, include_district=True, include_city=True, include_locality=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_building_query(
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
            must.append(self._multi_match_clause(query, ["building_name^5", "office_name^4", "road_name^3", "locality^2", "city_name^1.5", "district_name^1.25", "state_name^1", "full_address^2"]))
        must.extend(self._location_match_clauses(filters, include_building=True, include_road=True, include_locality=True, include_city=True, include_district=True, include_state=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_road_query(
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
            must.append(self._multi_match_clause(query, ["road_name^5", "building_name^3", "locality^2", "city_name^1.5", "district_name^1.25", "state_name^1", "full_address^2"]))
        must.extend(self._location_match_clauses(filters, include_road=True, include_building=True, include_locality=True, include_city=True, include_district=True, include_state=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_full_address_query(
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
            must.append(self._match_phrase_clause("full_address", query))
            should.append(self._multi_match_clause(query, self.BOOSTED_SEARCH_FIELDS))
        must.extend(self._location_match_clauses(filters, include_building=True, include_road=True, include_locality=True, include_city=True, include_district=True, include_state=True, include_pincode=True))
        return self._wrap_bool_query(must=must, should=should, filters=filters, geo=geo, size=size)

    def build_pincode_query(
        self,
        query: str | None,
        size: int,
        filters: dict[str, str | None],
        geo: dict[str, Any],
        parsed_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        should = self._boost_clauses(parsed_entities or {})
        pincode = filters.get("pincode") or (query if query and query.isdigit() else None)
        if pincode:
            must.append({"term": {"pincode": pincode}})
        must.extend(self._location_match_clauses(filters, include_city=True, include_locality=True, include_district=True, include_state=True))
        return self._wrap_bool_query(must=must, should=should, filters={**filters, "pincode": pincode}, geo=geo, size=size)

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
            must.append(self._multi_match_clause(filters.get("building") or query or "", ["building_name^4", "office_name^3", "road_name^2", "locality^1.5", "city_name^1.25", "district_name^1", "state_name^1", "full_address^2"]))
        must.extend(self._location_match_clauses(filters, include_building=True, include_road=True, include_locality=True, include_city=True, include_district=True, include_state=True, include_pincode=True))
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
            must.append(self._match_clause("city_name", filters["city"], boost=3))
        if filters.get("state"):
            must.append(self._match_clause("state_name", filters["state"], boost=2))
        if filters.get("pincode"):
            must.append({"term": {"pincode": filters["pincode"]}})
        elif query:
            must.append({"term": {"pincode": query}})
        must.extend(self._location_match_clauses(filters, include_locality=True, include_district=True, include_city=True, include_state=True, include_pincode=True))
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
            must.append(self._multi_match_clause(query, self.BOOSTED_SEARCH_FIELDS, fuzziness=self.fuzzy_fuzziness))

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
            return self.build_pincode_query(query, size, {**filters, "pincode": filters.get("pincode") or parsed_entities.get("pincode")}, geo, parsed_entities)
        if any(filters.get(key) for key in ("building", "locality", "city", "district", "state")):
            return self.build_building_query(query, size, filters, geo, parsed_entities)
        if query and query.isdigit() and len(query) == 6:
            return self.build_pincode_query(query, size, {**filters, "pincode": query}, geo, parsed_entities)
        if query and len(query.split()) >= 4:
            return self.build_full_address_query(query, size, filters, geo, parsed_entities)
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
            clauses.append(self._multi_match_clause(parsed_entities["building_name"], ["building_name^5", "office_name^4", "full_address^2"], query_type="phrase"))
        if parsed_entities.get("locality"):
            clauses.append(self._match_clause("locality", parsed_entities["locality"], boost=3))
        if parsed_entities.get("city"):
            clauses.append(self._match_clause("city_name", parsed_entities["city"], boost=2.5))
        if parsed_entities.get("district"):
            clauses.append(self._match_clause("district_name", parsed_entities["district"], boost=2))
        if parsed_entities.get("state"):
            clauses.append(self._match_clause("state_name", parsed_entities["state"], boost=1.5))
        if parsed_entities.get("pincode"):
            clauses.append({"term": {"pincode": parsed_entities["pincode"]}})
        if parsed_entities.get("road_name"):
            clauses.append(self._match_phrase_clause("road_name", parsed_entities["road_name"]))
        if parsed_entities.get("flat_number"):
            clauses.append(self._match_clause("full_address", parsed_entities["flat_number"], boost=1.5))
        return clauses

    @staticmethod
    def _filter_clauses(filters: dict[str, str | None]) -> list[dict[str, Any]]:
        clauses: list[dict[str, Any]] = []
        for key in ("pincode", "address_hash"):
            value = filters.get(key)
            if value:
                clauses.append({"term": {key if key == "pincode" else key: value}})
        return clauses

    @staticmethod
    def _match_clause(field: str, value: str, boost: float | int | None = None) -> dict[str, Any]:
        clause: dict[str, Any] = {"match": {field: {"query": value}}}
        if boost is not None:
            clause["match"][field]["boost"] = boost
        return clause

    def _match_phrase_clause(self, field: str, value: str) -> dict[str, Any]:
        return {"match_phrase": {field: {"query": value, "slop": self.phrase_slop}}}

    def _multi_match_clause(
        self,
        query: str,
        fields: list[str],
        *,
        query_type: str = "best_fields",
        fuzziness: str | None = None,
    ) -> dict[str, Any]:
        multi_match: dict[str, Any] = {
            "query": query,
            "type": query_type,
            "fields": fields,
        }
        if fuzziness is not None:
            multi_match["fuzziness"] = fuzziness
        return {"multi_match": multi_match}

    def _location_match_clauses(
        self,
        filters: dict[str, str | None],
        *,
        include_building: bool = False,
        include_road: bool = False,
        include_locality: bool = False,
        include_city: bool = False,
        include_district: bool = False,
        include_state: bool = False,
        include_pincode: bool = False,
        prefer_phrase: bool = False,
    ) -> list[dict[str, Any]]:
        clauses: list[dict[str, Any]] = []
        if include_building and filters.get("building"):
            clause = self._match_phrase_clause("building_name", filters["building"]) if prefer_phrase else self._match_clause("building_name", filters["building"], boost=4)
            clauses.append(clause)
        if include_road and filters.get("building"):
            clauses.append(self._match_clause("road_name", filters["building"], boost=3))
        if include_locality and filters.get("locality"):
            clause = self._match_phrase_clause("locality", filters["locality"]) if prefer_phrase else self._match_clause("locality", filters["locality"], boost=3)
            clauses.append(clause)
        if include_city and filters.get("city"):
            clause = self._match_phrase_clause("city_name", filters["city"]) if prefer_phrase else self._match_clause("city_name", filters["city"], boost=2.5)
            clauses.append(clause)
        if include_district and filters.get("district"):
            clause = self._match_phrase_clause("district_name", filters["district"]) if prefer_phrase else self._match_clause("district_name", filters["district"], boost=2)
            clauses.append(clause)
        if include_state and filters.get("state"):
            clause = self._match_phrase_clause("state_name", filters["state"]) if prefer_phrase else self._match_clause("state_name", filters["state"], boost=1.5)
            clauses.append(clause)
        if include_pincode and filters.get("pincode"):
            clauses.append({"term": {"pincode": filters["pincode"]}})
        return clauses
