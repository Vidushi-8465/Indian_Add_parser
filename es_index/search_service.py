"""Search strategy selection and execution."""

from __future__ import annotations

from typing import Any

from elasticsearch import Elasticsearch

from es_index.query_builder import QueryBuilder
from es_index.search_logger import SearchLogger


class SearchService:
    """Execute address searches and return ranked candidate sets."""

    STRATEGIES = {
        "exact",
        "fuzzy",
        "phrase",
        "autocomplete",
        "hierarchical_admin",
        "hierarchical_pincode",
        "geospatial",
        "auto",
    }

    def __init__(self, client: Elasticsearch, config: dict[str, Any]) -> None:
        self.client = client
        self.config = config
        self.index_name = config.get("index", {}).get("name", "indian_addresses")
        self.query_builder = QueryBuilder(config)
        self.search_logger = SearchLogger()
        search_config = config.get("search", {})
        self.default_size = int(search_config.get("default_size", 20))
        self.max_size = int(search_config.get("max_size", 100))
        self.geo_default_distance = search_config.get("geo_default_distance", "5km")

    def search(
        self,
        query: str | None = None,
        strategy: str = "auto",
        size: int | None = None,
        state: str | None = None,
        district: str | None = None,
        city: str | None = None,
        locality: str | None = None,
        building: str | None = None,
        pincode: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        distance: str | None = None,
    ) -> dict[str, Any]:
        selected_strategy = self._resolve_strategy(strategy, pincode=pincode, lat=lat, lon=lon, state=state)
        result_size = min(size or self.default_size, self.max_size)
        filters = {
            "state": state,
            "district": district,
            "city": city,
            "locality": locality,
            "building": building,
            "pincode": pincode,
        }
        geo = {
            "lat": lat,
            "lon": lon,
            "distance": distance or self.geo_default_distance,
        }

        body = self.query_builder.build_search_body(
            strategy=selected_strategy,
            query=query,
            size=result_size,
            filters=filters,
            geo=geo,
        )
        response = self.client.search(index=self.index_name, body=body)
        candidates = self._normalize_hits(response)
        result = {
            "query": query,
            "strategy": selected_strategy,
            "total_hits": response.get("hits", {}).get("total", {}).get("value", len(candidates)),
            "took_ms": response.get("took", 0),
            "candidates": candidates,
        }
        self.search_logger.log_search(
            strategy=selected_strategy,
            request={
                "query": query,
                "size": result_size,
                "filters": filters,
                "geo": geo,
            },
            response_summary={
                "total_hits": result["total_hits"],
                "took_ms": result["took_ms"],
                "candidate_count": len(candidates),
            },
        )
        return result

    def _resolve_strategy(
        self,
        strategy: str,
        pincode: str | None,
        lat: float | None,
        lon: float | None,
        state: str | None,
    ) -> str:
        if strategy != "auto":
            return strategy if strategy in self.STRATEGIES else "auto"
        if lat is not None and lon is not None:
            return "geospatial"
        if pincode:
            return "hierarchical_pincode"
        if state:
            return "hierarchical_admin"
        return "auto"

    @staticmethod
    def _normalize_hits(response: dict[str, Any]) -> list[dict[str, Any]]:
        hits = response.get("hits", {}).get("hits", [])
        candidates: list[dict[str, Any]] = []
        for hit in hits:
            source = hit.get("_source", {})
            candidates.append(
                {
                    "id": hit.get("_id"),
                    "score": float(hit.get("_score") or 0.0),
                    "address_hash": source.get("address_hash"),
                    "full_address": source.get("full_address"),
                    "building_name": source.get("building_name"),
                    "road_name": source.get("road_name"),
                    "locality": source.get("locality"),
                    "city_name": source.get("city_name"),
                    "district_name": source.get("district_name"),
                    "subdistrict_name": source.get("subdistrict_name"),
                    "state_name": source.get("state_name"),
                    "pincode": source.get("pincode"),
                    "office_name": source.get("office_name"),
                    "latitude": source.get("latitude"),
                    "longitude": source.get("longitude"),
                    "location": source.get("location"),
                    "quality_score": source.get("quality_score"),
                    "source_file": source.get("source_file"),
                }
            )
        return candidates
