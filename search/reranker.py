"""Candidate reranking and confidence scoring for search results."""

from __future__ import annotations

from search.search_results import SearchCandidate, SearchEntities

from ranking.ranker import MLRanker


class ResultReranker:
    """Rank ES candidates with an ML model when available."""

    def __init__(self, config: dict | None = None, model_path: str | None = None) -> None:
        ranking_config = (config or {}).get("ranking", {})
        resolved_model_path = model_path or ranking_config.get("model_path")
        self.rank_model = MLRanker(model_path=resolved_model_path)

    def rerank(
        self,
        query: str | None,
        parsed_entities: SearchEntities,
        hits: list[SearchCandidate],
    ) -> list[SearchCandidate]:
        if not hits:
            return []
        return self.rank_model.rank_candidates(query, parsed_entities, hits)
