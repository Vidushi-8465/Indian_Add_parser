"""Feature engineering for query-candidate ranking pairs."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from search.search_results import SearchCandidate, SearchEntities

from .similarity import (
    common_token_count,
    exact_match,
    jaccard_similarity,
    normalize_text,
    partial_ratio,
    safe_ratio,
    token_overlap_percent,
    token_set_ratio,
    token_sort_ratio,
    tokenize,
)


@dataclass(slots=True)
class RankingFeatureVector:
    """A single numeric feature vector."""

    values: dict[str, float]

    def as_ordered_list(self, feature_names: list[str]) -> list[float]:
        return [float(self.values.get(name, 0.0)) for name in feature_names]


class RankingFeatureBuilder:
    """Build ML ranking features for a query-candidate pair."""

    FIELD_PAIRS = [
        ("full_address", "full_address"),
        ("building_name", "building_name"),
        ("road_name", "road_name"),
        ("locality", "locality"),
        ("city", "city_name"),
        ("district", "district_name"),
        ("state", "state_name"),
    ]

    EXACT_FIELDS = [
        ("building_name", "building_name"),
        ("road_name", "road_name"),
        ("locality", "locality"),
        ("city", "city_name"),
        ("district", "district_name"),
        ("state", "state_name"),
        ("pincode", "pincode"),
    ]

    def build_feature_row(
        self,
        query: str | None,
        parsed_entities: SearchEntities,
        candidate: SearchCandidate,
        *,
        candidate_rank: int | None = None,
        retrieval_position: int | None = None,
        query_lat: float | None = None,
        query_lon: float | None = None,
    ) -> RankingFeatureVector:
        normalized_query = normalize_text(query)
        candidate_address = self._candidate_text(candidate)

        query_has_geo = query_lat is not None and query_lon is not None
        candidate_lat = self._extract_geo_coordinate(candidate.latitude, candidate.location, "lat")
        candidate_lon = self._extract_geo_coordinate(candidate.longitude, candidate.location, "lon")
        candidate_has_geo = candidate_lat is not None and candidate_lon is not None
        geo_distance_km = self._geo_distance_km(query_lat, query_lon, candidate)
        features: dict[str, float] = {
            "query_length": float(len(tokenize(query))),
            "candidate_length": float(len(tokenize(candidate_address))),
            "candidate_bm25_score": float(candidate.bm25_score or candidate.score or 0.0),
            "candidate_quality_score": self._numeric(candidate.quality_score),
            "candidate_rank": float(candidate_rank or retrieval_position or candidate.es_rank or 0),
            "retrieval_position": float(retrieval_position or candidate.retrieval_position or 0),
            "has_latitude": self._has_geo_value(candidate.latitude),
            "has_longitude": self._has_geo_value(candidate.longitude),
            "geo_distance_km": geo_distance_km,
            "geo_distance_available": 1.0 if query_has_geo and candidate_has_geo else 0.0,
            "field_presence_count": float(self._field_presence_count(candidate)),
        }

        for query_field, candidate_field in self.FIELD_PAIRS:
            query_value = self._query_field_value(parsed_entities, query, query_field)
            candidate_value = self._candidate_field_value(candidate, candidate_field)
            prefix = f"{query_field}__{candidate_field}"
            features[f"{prefix}__ratio"] = safe_ratio(query_value, candidate_value)
            features[f"{prefix}__partial_ratio"] = partial_ratio(query_value, candidate_value)
            features[f"{prefix}__token_sort_ratio"] = token_sort_ratio(query_value, candidate_value)
            features[f"{prefix}__token_set_ratio"] = token_set_ratio(query_value, candidate_value)
            features[f"{prefix}__common_token_count"] = common_token_count(query_value, candidate_value)
            features[f"{prefix}__token_overlap_percent"] = token_overlap_percent(query_value, candidate_value)
            features[f"{prefix}__jaccard_similarity"] = jaccard_similarity(query_value, candidate_value)
            features[f"{prefix}__exact_match"] = float(exact_match(query_value, candidate_value))

        for query_field, candidate_field in self.EXACT_FIELDS:
            query_value = self._query_field_value(parsed_entities, query, query_field)
            candidate_value = self._candidate_field_value(candidate, candidate_field)
            features[f"exact_{query_field}"] = float(exact_match(query_value, candidate_value))

        features["query_candidate_token_common"] = common_token_count(normalized_query, candidate_address)
        features["query_candidate_token_overlap"] = token_overlap_percent(normalized_query, candidate_address)
        features["query_candidate_jaccard"] = jaccard_similarity(normalized_query, candidate_address)

        return RankingFeatureVector(features)

    def build_feature_matrix(
        self,
        query: str | None,
        parsed_entities: SearchEntities,
        candidates: list[SearchCandidate],
        *,
        query_lat: float | None = None,
        query_lon: float | None = None,
    ) -> tuple[list[RankingFeatureVector], list[str]]:
        rows: list[RankingFeatureVector] = []
        for index, candidate in enumerate(candidates, start=1):
            rows.append(
                self.build_feature_row(
                    query,
                    parsed_entities,
                    candidate,
                    candidate_rank=index,
                    retrieval_position=index,
                    query_lat=query_lat,
                    query_lon=query_lon,
                )
            )
        feature_names = self.feature_names(rows)
        return rows, feature_names

    @staticmethod
    def feature_names(rows: list[RankingFeatureVector] | None = None) -> list[str]:
        if rows:
            names: list[str] = []
            seen: set[str] = set()
            for row in rows:
                for name in row.values:
                    if name not in seen:
                        seen.add(name)
                        names.append(name)
            return names
        return [
            "query_length",
            "candidate_length",
            "candidate_bm25_score",
            "candidate_quality_score",
            "candidate_rank",
            "retrieval_position",
            "has_latitude",
            "has_longitude",
            "geo_distance_km",
            "geo_distance_available",
            "field_presence_count",
        ]

    @staticmethod
    def _numeric(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _has_geo_value(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        try:
            return 1.0 if math.isfinite(float(value)) else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _candidate_text(candidate: SearchCandidate) -> str:
        parts = [
            candidate.full_address,
            candidate.building_name,
            candidate.road_name,
            candidate.locality,
            candidate.city_name,
            candidate.district_name,
            candidate.state_name,
            candidate.pincode,
            candidate.office_name,
        ]
        return " ".join(part for part in parts if part)

    @staticmethod
    def _candidate_field_value(candidate: SearchCandidate, field_name: str) -> str | None:
        return getattr(candidate, field_name, None)

    @staticmethod
    def _query_field_value(parsed_entities: SearchEntities, query: str | None, field_name: str) -> str | None:
        if field_name == "full_address":
            return query
        return getattr(parsed_entities, field_name, None) or query

    def _geo_distance_km(self, query_lat: float | None, query_lon: float | None, candidate: SearchCandidate) -> float:
        if query_lat is None or query_lon is None:
            return 0.0

        candidate_lat = self._extract_geo_coordinate(candidate.latitude, candidate.location, "lat")
        candidate_lon = self._extract_geo_coordinate(candidate.longitude, candidate.location, "lon")
        if candidate_lat is None or candidate_lon is None:
            return 0.0

        return float(self._haversine_km(query_lat, query_lon, candidate_lat, candidate_lon))

    @staticmethod
    def _extract_geo_coordinate(value: Any, location: Any, key: str) -> float | None:
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        if isinstance(location, dict):
            coordinate = location.get(key)
            if coordinate not in (None, ""):
                try:
                    return float(coordinate)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius_km * c

    @staticmethod
    def _field_presence_count(candidate: SearchCandidate) -> int:
        fields = [
            candidate.full_address,
            candidate.building_name,
            candidate.road_name,
            candidate.locality,
            candidate.city_name,
            candidate.district_name,
            candidate.state_name,
            candidate.pincode,
            candidate.office_name,
            candidate.latitude,
            candidate.longitude,
        ]
        return sum(1 for value in fields if value not in (None, ""))
