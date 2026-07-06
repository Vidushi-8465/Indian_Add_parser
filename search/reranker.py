"""Candidate reranking and confidence scoring for search results."""

from __future__ import annotations

from dataclasses import dataclass

from .search_results import SearchCandidate, SearchEntities


@dataclass(slots=True)
class RerankWeights:
    exact_building: float = 18.0
    exact_locality: float = 12.0
    exact_city: float = 10.0
    exact_district: float = 8.0
    exact_state: float = 8.0
    exact_pincode: float = 20.0
    phrase_match: float = 6.0
    completeness: float = 2.0
    quality_score: float = 0.08


class ResultReranker:
    """Score and sort hits using a small heuristic model."""

    def __init__(self, weights: RerankWeights | None = None) -> None:
        self.weights = weights or RerankWeights()

    def rerank(
        self,
        query: str | None,
        parsed_entities: SearchEntities,
        hits: list[SearchCandidate],
    ) -> list[SearchCandidate]:
        if not hits:
            return []

        scored: list[SearchCandidate] = []
        for candidate in hits:
            score = self._score_candidate(query=query, parsed_entities=parsed_entities, candidate=candidate)
            candidate.score = score
            scored.append(candidate)

        top_score = max(candidate.score for candidate in scored) or 1.0
        for candidate in scored:
            candidate.confidence = round(min(0.99, candidate.score / top_score), 4)

        scored.sort(key=lambda item: (item.score, item.confidence), reverse=True)
        return scored

    def _score_candidate(
        self,
        query: str | None,
        parsed_entities: SearchEntities,
        candidate: SearchCandidate,
    ) -> float:
        score = float(candidate.score or 0.0)
        normalized_query = (query or "").strip().lower()

        if parsed_entities.building_name and self._matches(candidate.building_name, parsed_entities.building_name):
            score += self.weights.exact_building
        if parsed_entities.locality and self._matches(candidate.locality, parsed_entities.locality):
            score += self.weights.exact_locality
        if parsed_entities.city and self._matches(candidate.city_name, parsed_entities.city):
            score += self.weights.exact_city
        if parsed_entities.district and self._matches(candidate.district_name, parsed_entities.district):
            score += self.weights.exact_district
        if parsed_entities.state and self._matches(candidate.state_name, parsed_entities.state):
            score += self.weights.exact_state
        if parsed_entities.pincode and self._matches(candidate.pincode, parsed_entities.pincode):
            score += self.weights.exact_pincode

        if normalized_query and candidate.full_address:
            if normalized_query in candidate.full_address.lower():
                score += self.weights.phrase_match

        score += self._completeness_score(candidate)

        if candidate.quality_score is not None:
            score += float(candidate.quality_score) * self.weights.quality_score

        return round(score, 4)

    @staticmethod
    def _matches(left: str | None, right: str | None) -> bool:
        if not left or not right:
            return False
        return left.strip().lower() == right.strip().lower()

    def _completeness_score(self, candidate: SearchCandidate) -> float:
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
        ]
        present = sum(1 for value in fields if value not in (None, ""))
        return present * self.weights.completeness
