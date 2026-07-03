"""Pydantic schemas for the search API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SearchStrategy = Literal[
    "auto",
    "exact",
    "fuzzy",
    "phrase",
    "autocomplete",
    "hierarchical_admin",
    "hierarchical_pincode",
    "geospatial",
]


class SearchRequest(BaseModel):
    query: str | None = Field(default=None, description="Free-text address query")
    strategy: SearchStrategy = Field(default="auto")
    size: int = Field(default=20, ge=1, le=100)
    state: str | None = None
    district: str | None = None
    city: str | None = None
    locality: str | None = None
    building: str | None = None
    pincode: str | None = None
    lat: float | None = None
    lon: float | None = None
    distance: str | None = Field(default="5km")


class AddressCandidate(BaseModel):
    id: str | None = None
    score: float = 0.0
    address_hash: str | None = None
    full_address: str | None = None
    building_name: str | None = None
    road_name: str | None = None
    locality: str | None = None
    city_name: str | None = None
    district_name: str | None = None
    subdistrict_name: str | None = None
    state_name: str | None = None
    pincode: str | None = None
    office_name: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    location: dict[str, Any] | None = None
    quality_score: float | None = None
    source_file: str | None = None


class SearchResponse(BaseModel):
    query: str | None
    strategy: str
    total_hits: int
    took_ms: int
    candidates: list[AddressCandidate]
