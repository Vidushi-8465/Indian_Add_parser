"""FastAPI application for address search.

Wires the HTTP layer to the full ``search`` pipeline (query normalization,
entity detection, intent detection, Elasticsearch retrieval, candidate
deduplication, and ML/heuristic re-ranking).
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query

from api.schemas import AddressCandidate, SearchRequest, SearchResponse
from es_index.client import build_elasticsearch_client, ping_cluster
from search.search_service import SearchService
from utils.constants import DEFAULT_APP_CONFIG, DEFAULT_ELASTICSEARCH_CONFIG
from utils.file_utils import load_yaml_config


@lru_cache
def get_app_config() -> dict:
    return load_yaml_config(DEFAULT_APP_CONFIG)


@lru_cache
def get_search_service() -> SearchService:
    es_config = load_yaml_config(DEFAULT_ELASTICSEARCH_CONFIG)
    client = build_elasticsearch_client(es_config)
    return SearchService(client, es_config)


def _default_size() -> int:
    return int(get_app_config().get("api", {}).get("top_k", 20))


def _require_cluster(service: SearchService) -> None:
    if not ping_cluster(service.client):
        raise HTTPException(status_code=503, detail="Elasticsearch cluster unavailable")


def _to_response(result: dict) -> SearchResponse:
    candidates = [AddressCandidate(**candidate) for candidate in result.get("candidates", [])]
    return SearchResponse(
        query=result.get("query"),
        strategy=result.get("strategy", "auto"),
        total_hits=int(result.get("total_hits", 0)),
        took_ms=int(result.get("took_ms", 0)),
        best_match=result.get("best_match"),
        candidates=candidates,
    )


def create_app() -> FastAPI:
    app_config = get_app_config()
    api_config = app_config.get("api", {})
    app = FastAPI(
        title=api_config.get("title", "Indian Address Geocoding API"),
        description=api_config.get("description", "Address search API"),
        version=api_config.get("version", "1.0.0"),
    )

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        service = get_search_service()
        connected = ping_cluster(service.client)
        return {
            "status": "ok" if connected else "degraded",
            "elasticsearch": connected,
            "index": service.index_name,
        }

    @app.post("/search", response_model=SearchResponse)
    def search_addresses(request: SearchRequest) -> SearchResponse:
        service = get_search_service()
        _require_cluster(service)
        result = service.search(
            query=request.query,
            strategy=request.strategy,
            size=request.size or _default_size(),
            state=request.state,
            district=request.district,
            city=request.city,
            locality=request.locality,
            building=request.building,
            pincode=request.pincode,
            lat=request.lat,
            lon=request.lon,
            distance=request.distance,
        )
        return _to_response(result)

    @app.get("/autocomplete", response_model=SearchResponse)
    def autocomplete(
        q: str = Query(..., min_length=1, description="Partial address text"),
        size: int = Query(10, ge=1, le=50),
    ) -> SearchResponse:
        service = get_search_service()
        _require_cluster(service)
        result = service.search(query=q, strategy="autocomplete", size=size)
        return _to_response(result)

    @app.get("/suggest", response_model=SearchResponse)
    def suggest(
        q: str = Query(..., min_length=1, description="Address query to get suggestions for"),
        size: int = Query(10, ge=1, le=50),
    ) -> SearchResponse:
        service = get_search_service()
        _require_cluster(service)
        result = service.search(query=q, strategy="fuzzy", size=size)
        return _to_response(result)

    @app.get("/nearby", response_model=SearchResponse)
    def nearby(
        lat: float = Query(..., ge=-90, le=90),
        lon: float = Query(..., ge=-180, le=180),
        distance: str = Query("5km", description="Geo radius, e.g. 2km, 500m"),
        q: str | None = Query(None, description="Optional text filter"),
        size: int = Query(20, ge=1, le=100),
    ) -> SearchResponse:
        service = get_search_service()
        _require_cluster(service)
        result = service.search(query=q, strategy="geospatial", lat=lat, lon=lon, distance=distance, size=size)
        return _to_response(result)

    @app.get("/reverse-geocode", response_model=SearchResponse)
    def reverse_geocode(
        lat: float = Query(..., ge=-90, le=90),
        lon: float = Query(..., ge=-180, le=180),
        distance: str = Query("2km", description="Search radius for the nearest address"),
    ) -> SearchResponse:
        service = get_search_service()
        _require_cluster(service)
        result = service.search(strategy="geospatial", lat=lat, lon=lon, distance=distance, size=1)
        return _to_response(result)

    return app


app = create_app()
