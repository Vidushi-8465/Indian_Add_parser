"""FastAPI application for address search."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException

from api.schemas import AddressCandidate, SearchRequest, SearchResponse
from es_index.client import build_elasticsearch_client, ping_cluster
from es_index.search_service import SearchService
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
        return {
            "status": "ok" if ping_cluster(service.client) else "degraded",
            "elasticsearch": ping_cluster(service.client),
            "index": service.index_name,
        }

    @app.post("/search", response_model=SearchResponse)
    def search_addresses(request: SearchRequest) -> SearchResponse:
        service = get_search_service()
        if not ping_cluster(service.client):
            raise HTTPException(status_code=503, detail="Elasticsearch cluster unavailable")

        default_size = int(get_app_config().get("api", {}).get("top_k", 20))
        result = service.search(
            query=request.query,
            strategy=request.strategy,
            size=request.size or default_size,
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
        candidates = [AddressCandidate(**candidate) for candidate in result["candidates"]]
        return SearchResponse(
            query=result["query"],
            strategy=result["strategy"],
            total_hits=int(result["total_hits"]),
            took_ms=int(result["took_ms"]),
            candidates=candidates,
        )

    return app


app = create_app()
