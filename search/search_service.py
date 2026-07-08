"""High-level address search orchestration."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from .entity_detector import EntityDetector
from .query_builder import QueryBuilder
from .query_normalizer import QueryNormalizer
from .query_parser import QueryParser
from .reranker import ResultReranker
from .search_results import SearchAnalysis, SearchCandidate, SearchEntities, SearchResult
from app_logging.logger import setup_logging
from es_index.client import build_elasticsearch_client, test_connection

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SearchPlan:
    strategy: str
    analysis: SearchAnalysis
    filters: dict[str, str | None]
    geo: dict[str, Any]
    size: int
    query_body: dict[str, Any]


class SearchService:
    """Normalize, analyze, execute, and rerank address searches."""

    STRATEGIES = {
        "exact",
        "fuzzy",
        "phrase",
        "autocomplete",
        "city",
        "locality",
        "district",
        "state",
        "building",
        "road",
        "full_address",
        "pincode",
        "hierarchical_admin",
        "hierarchical_pincode",
        "geospatial",
        "auto",
    }

    def __init__(self, client: Any | None, config: dict[str, Any]) -> None:
        self.client = client
        self.config = config
        self.index_name = config.get("index", {}).get("name", "indian_addresses")
        self.query_builder = QueryBuilder(config)
        self.normalizer = QueryNormalizer()
        self.parser = QueryParser(self.normalizer)
        self.entity_detector = EntityDetector(self.normalizer)
        self.reranker = ResultReranker(config=config)
        search_config = config.get("search", {})
        self.default_size = int(search_config.get("default_size", 20))
        self.max_size = int(search_config.get("max_size", 100))
        self.top_n = int(search_config.get("top_n", 100))
        self.geo_default_distance = search_config.get("geo_default_distance", "5km")

    def analyze_query(self, query: str | None) -> SearchAnalysis:
        parsed = self.parser.parse(query)
        entities = self.entity_detector.detect(query, parsed.tokens)
        parsed_entities = self._merge_entities(entities)
        return SearchAnalysis(
            query=query,
            normalized_query=parsed.normalized_query,
            intent=parsed.intent,
            tokens=parsed.tokens,
            phrases=parsed.phrases,
            parsed_entities=parsed_entities,
            validation_errors=parsed.validation_errors,
        )

    def build_search_plan(
        self,
        query: str | None,
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
    ) -> SearchPlan:
        analysis = self.analyze_query(query)
        resolved_strategy = self._resolve_strategy(
            strategy,
            analysis.intent,
            pincode=pincode or analysis.parsed_entities.pincode,
            lat=lat,
            lon=lon,
            state=state or analysis.parsed_entities.state,
        )
        result_size = min(size or self.default_size, self.max_size)
        retrieval_size = self.top_n
        filters = self._build_filters(
            analysis.parsed_entities,
            state=state,
            district=district,
            city=city,
            locality=locality,
            building=building,
            pincode=pincode,
        )
        geo = {
            "lat": lat,
            "lon": lon,
            "distance": distance or self.geo_default_distance,
        }
        query_body = self.query_builder.build_search_body(
            strategy=resolved_strategy,
            query=analysis.normalized_query or query,
            size=retrieval_size,
            filters=filters,
            geo=geo,
            parsed_entities=analysis.parsed_entities.to_dict(),
        )
        return SearchPlan(
            strategy=resolved_strategy,
            analysis=analysis,
            filters=filters,
            geo=geo,
            size=result_size,
            query_body=query_body,
        )

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
        if self.client is None:
            raise RuntimeError("SearchService.search requires an Elasticsearch client.")

        start_time = perf_counter()
        plan = self.build_search_plan(
            query=query,
            strategy=strategy,
            size=size,
            state=state,
            district=district,
            city=city,
            locality=locality,
            building=building,
            pincode=pincode,
            lat=lat,
            lon=lon,
            distance=distance,
        )

        response = self.client.search(index=self.index_name, body=plan.query_body)
        raw_hits = response.get("hits", {}).get("hits", [])
        total_hits = response.get("hits", {}).get("total", {})
        if isinstance(total_hits, dict):
            total_count = int(total_hits.get("value", len(raw_hits)))
        else:
            total_count = int(total_hits or len(raw_hits))

        candidates = self._retrieve_candidates(raw_hits)
        ranked = self.reranker.rerank(plan.analysis.normalized_query or query, plan.analysis.parsed_entities, candidates)
        execution_time_ms = int((perf_counter() - start_time) * 1000)
        final_results = ranked[: plan.size]

        result = SearchResult(
            query=query,
            normalized_query=plan.analysis.normalized_query,
            intent=plan.analysis.intent,
            parsed_entities=plan.analysis.parsed_entities,
            retrieved_candidates=candidates,
            results=final_results,
            execution_time_ms=execution_time_ms,
            total_hits=total_count,
            strategy=plan.strategy,
            validation_errors=plan.analysis.validation_errors,
        )

        LOGGER.info(
            "search query=%s strategy=%s hits=%s time_ms=%s",
            query,
            plan.strategy,
            total_count,
            execution_time_ms,
        )
        return result.to_dict()

    def preview(
        self,
        query: str | None = None,
        strategy: str = "auto",
        size: int | None = None,
        **filters: Any,
    ) -> dict[str, Any]:
        plan = self.build_search_plan(query=query, strategy=strategy, size=size, **filters)
        return {
            "analysis": plan.analysis.to_dict(),
            "strategy": plan.strategy,
            "filters": plan.filters,
            "geo": plan.geo,
            "size": plan.size,
            "query_body": plan.query_body,
        }

    def retrieve_candidates(
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
        """Return the raw ES candidate pool before reranking."""
        if self.client is None:
            raise RuntimeError("SearchService.retrieve_candidates requires an Elasticsearch client.")

        plan = self.build_search_plan(
            query=query,
            strategy=strategy,
            size=size,
            state=state,
            district=district,
            city=city,
            locality=locality,
            building=building,
            pincode=pincode,
            lat=lat,
            lon=lon,
            distance=distance,
        )
        response = self.client.search(index=self.index_name, body=plan.query_body)
        raw_hits = response.get("hits", {}).get("hits", [])
        total_hits = response.get("hits", {}).get("total", {})
        if isinstance(total_hits, dict):
            total_count = int(total_hits.get("value", len(raw_hits)))
        else:
            total_count = int(total_hits or len(raw_hits))

        candidates = self._retrieve_candidates(raw_hits)
        return {
            "query": query,
            "strategy": plan.strategy,
            "total_hits": total_count,
            "retrieval_size": self.top_n,
            "candidates": [candidate.to_dict() for candidate in candidates],
            "query_body": plan.query_body,
        }

    @staticmethod
    def _retrieve_candidates(raw_hits: list[dict[str, Any]]) -> list[SearchCandidate]:
        return [SearchCandidate.from_hit(hit) for hit in raw_hits]

    @staticmethod
    def _merge_entities(entities: SearchEntities) -> SearchEntities:
        return entities

    @staticmethod
    def _build_filters(
        parsed_entities: SearchEntities,
        state: str | None = None,
        district: str | None = None,
        city: str | None = None,
        locality: str | None = None,
        building: str | None = None,
        pincode: str | None = None,
    ) -> dict[str, str | None]:
        return {
            "state": state or parsed_entities.state,
            "district": district or parsed_entities.district,
            "city": city or parsed_entities.city,
            "locality": locality or parsed_entities.locality,
            "building": building or parsed_entities.building_name,
            "pincode": pincode or parsed_entities.pincode,
        }

    def _resolve_strategy(
        self,
        strategy: str,
        intent: str,
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
            return "pincode"
        if intent == "PINCODE_SEARCH":
            return "pincode"
        if intent == "CITY_SEARCH":
            return "city"
        if intent == "LOCALITY_SEARCH":
            return "locality"
        if intent == "DISTRICT_SEARCH":
            return "district"
        if intent == "STATE_SEARCH":
            return "state"
        if intent == "BUILDING_SEARCH":
            return "building"
        if intent == "ROAD_SEARCH":
            return "road"
        if intent == "FULL_ADDRESS_SEARCH":
            return "full_address"
        if state:
            return "state"
        return "fuzzy"


def _load_json_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    import yaml

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a mapping.")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Indian Address Search")

    parser.add_argument(
        "--config",
        default=Path(__file__).resolve().parents[1] / "configs" / "elasticsearch.yaml",
    )

    parser.add_argument("--query", required=True)
    parser.add_argument("--strategy", default="auto")
    parser.add_argument("--size", type=int, default=20)

    parser.add_argument("--state")
    parser.add_argument("--district")
    parser.add_argument("--city")
    parser.add_argument("--locality")
    parser.add_argument("--building")
    parser.add_argument("--pincode")

    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--distance")

    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    setup_logging()

    config = _load_json_config(args.config)

    if args.dry_run:
        service = SearchService(client=None, config=config)

        preview = service.preview(
            query=args.query,
            strategy=args.strategy,
            size=args.size,
            state=args.state,
            district=args.district,
            city=args.city,
            locality=args.locality,
            building=args.building,
            pincode=args.pincode,
            lat=args.lat,
            lon=args.lon,
            distance=args.distance,
        )

        print(json.dumps(preview, indent=2, ensure_ascii=False))
        return

    client = build_elasticsearch_client(config)

    status = test_connection(client, config)

    if not status["connected"]:
        raise RuntimeError("Could not connect to Elasticsearch.")

    service = SearchService(client=client, config=config)

    result = service.search(
        query=args.query,
        strategy=args.strategy,
        size=args.size,
        state=args.state,
        district=args.district,
        city=args.city,
        locality=args.locality,
        building=args.building,
        pincode=args.pincode,
        lat=args.lat,
        lon=args.lon,
        distance=args.distance,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
