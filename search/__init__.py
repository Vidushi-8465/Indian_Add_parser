"""Search package for query analysis, query building, and ranking."""

from __future__ import annotations

from typing import Any

# Lightweight exports only — keep heavy modules lazy to avoid circular imports
# (ranking.feature_engineering → search → reranker → ranking.ranker → feature_engineering).
from .search_results import SearchAnalysis, SearchCandidate, SearchEntities, SearchResult

__all__ = [
    "EntityDetector",
    "QueryBuilder",
    "QueryNormalizer",
    "QueryParser",
    "ResultReranker",
    "SearchAnalysis",
    "SearchCandidate",
    "SearchEntities",
    "SearchResult",
    "SearchService",
]


def __getattr__(name: str) -> Any:
    if name == "EntityDetector":
        from .entity_detector import EntityDetector

        return EntityDetector
    if name == "QueryBuilder":
        from .query_builder import QueryBuilder

        return QueryBuilder
    if name == "QueryNormalizer":
        from .query_normalizer import QueryNormalizer

        return QueryNormalizer
    if name == "QueryParser":
        from .query_parser import QueryParser

        return QueryParser
    if name == "ResultReranker":
        from .reranker import ResultReranker

        return ResultReranker
    if name == "SearchService":
        from .search_service import SearchService

        return SearchService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
