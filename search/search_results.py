"""Dataclasses for structured search analysis and results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _compact_mapping(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


def _confidence_label(confidence: float | None) -> str:
    value = float(confidence or 0.0)
    if value >= 0.80:
        return "high"
    if value >= 0.60:
        return "medium"
    return "low"


def _values_match(query_value: Any, candidate_value: Any) -> bool:
    if not query_value or not candidate_value:
        return False
    return str(query_value).strip().casefold() == str(candidate_value).strip().casefold()


@dataclass(slots=True)
class SearchEntities:
    building_name: str | None = None
    office_name: str | None = None
    landmark: str | None = None
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
        # Keep lists ordered by confidence (highest first).
        ordered_results = sorted(
            self.results,
            key=lambda candidate: (candidate.confidence, candidate.score, candidate.bm25_score),
            reverse=True,
        )
        ordered_retrieved = sorted(
            self.retrieved_candidates,
            key=lambda candidate: (candidate.confidence, candidate.score, candidate.bm25_score),
            reverse=True,
        )
        result_items = [candidate.to_dict() for candidate in ordered_results]
        retrieved_items = [candidate.to_dict() for candidate in ordered_retrieved]
        best = self.best_match(pool=ordered_results or ordered_retrieved)
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "intent": self.intent,
            "strategy": self.strategy,
            "parsed_entities": self.parsed_entities.to_dict(),
            "best_match": best,
            "results": result_items,
            "candidates": result_items,
            "retrieved_candidates": retrieved_items,
            "took_ms": self.execution_time_ms,
            "execution_time_ms": self.execution_time_ms,
            "total_hits": self.total_hits,
            "validation_errors": list(self.validation_errors),
        }

    def best_match(
        self,
        pool: list[SearchCandidate] | None = None,
    ) -> dict[str, Any] | None:
        """The single best address: the candidate with the highest confidence.

        Ties are broken by score, then BM25, so the strongest overall match wins.
        """
        candidates = pool if pool is not None else self.results
        if not candidates:
            return None
        best = max(
            candidates,
            key=lambda candidate: (candidate.confidence, candidate.score, candidate.bm25_score),
        )
        return {
            "full_address": best.full_address,
            "confidence": best.confidence,
            "confidence_label": _confidence_label(best.confidence),
            "score": best.score,
            "building_name": best.building_name,
            "office_name": best.office_name,
            "road_name": best.road_name,
            "locality": best.locality,
            "city_name": best.city_name,
            "district_name": best.district_name,
            "state_name": best.state_name,
            "pincode": best.pincode,
            "latitude": best.latitude,
            "longitude": best.longitude,
            "explanation": self._match_explanation(best),
        }

    def _match_explanation(self, candidate: "SearchCandidate") -> str:
        entity = self.parsed_entities
        checks = [
            ("pincode", entity.pincode, candidate.pincode),
            ("building", entity.building_name, candidate.building_name),
            ("office", entity.office_name, candidate.office_name),
            ("road", entity.road_name, candidate.road_name),
            ("locality", entity.locality, candidate.locality),
            ("city", entity.city, candidate.city_name),
            ("district", entity.district, candidate.district_name),
            ("state", entity.state, candidate.state_name),
        ]
        matched = [name for name, query_value, candidate_value in checks if _values_match(query_value, candidate_value)]
        label = _confidence_label(candidate.confidence)
        if matched:
            return f"{label} confidence — matched on {', '.join(matched)}"
        return f"{label} confidence — best text/similarity match"
