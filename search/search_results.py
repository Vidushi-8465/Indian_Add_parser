"""Dataclasses for structured search analysis and results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _compact_mapping(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


@dataclass(slots=True)
class SearchEntities:
    building_name: str | None = None
    flat_number: str | None = None
    road_name: str | None = None
    locality: str | None = None
    village: str | None = None
    block: str | None = None
    taluka: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _compact_mapping(asdict(self))


@dataclass(slots=True)
class SearchCandidate:
    id: str | None = None
    score: float = 0.0
    bm25_score: float = 0.0
    confidence: float = 0.0
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
    es_rank: int | None = None
    retrieval_position: int | None = None

    @classmethod
    def from_hit(cls, hit: dict[str, Any]) -> "SearchCandidate":
        source = hit.get("_source", {})
        return cls(
            id=hit.get("_id"),
            score=float(hit.get("_score") or 0.0),
            bm25_score=float(hit.get("_score") or 0.0),
            address_hash=source.get("address_hash"),
            full_address=source.get("full_address"),
            building_name=source.get("building_name"),
            road_name=source.get("road_name"),
            locality=source.get("locality"),
            city_name=source.get("city_name"),
            district_name=source.get("district_name"),
            subdistrict_name=source.get("subdistrict_name"),
            state_name=source.get("state_name"),
            pincode=source.get("pincode"),
            office_name=source.get("office_name"),
            latitude=source.get("latitude"),
            longitude=source.get("longitude"),
            location=source.get("location"),
            quality_score=source.get("quality_score"),
            source_file=source.get("source_file"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _compact_mapping(asdict(self))


@dataclass(slots=True)
class SearchAnalysis:
    query: str | None
    normalized_query: str
    intent: str
    tokens: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    parsed_entities: SearchEntities = field(default_factory=SearchEntities)
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "intent": self.intent,
            "tokens": list(self.tokens),
            "phrases": list(self.phrases),
            "parsed_entities": self.parsed_entities.to_dict(),
            "validation_errors": list(self.validation_errors),
        }


@dataclass(slots=True)
class SearchResult:
    query: str | None
    normalized_query: str
    intent: str
    parsed_entities: SearchEntities
    retrieved_candidates: list[SearchCandidate] = field(default_factory=list)
    results: list[SearchCandidate] = field(default_factory=list)
    execution_time_ms: int = 0
    total_hits: int = 0
    strategy: str = "auto"
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        retrieved_items = [candidate.to_dict() for candidate in self.retrieved_candidates]
        result_items = [candidate.to_dict() for candidate in self.results]
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "intent": self.intent,
            "strategy": self.strategy,
            "parsed_entities": self.parsed_entities.to_dict(),
            "retrieved_candidates": retrieved_items,
            "results": result_items,
            "candidates": result_items,
            "execution_time_ms": self.execution_time_ms,
            "total_hits": self.total_hits,
            "validation_errors": list(self.validation_errors),
        }
