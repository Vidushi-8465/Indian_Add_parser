"""ML ranking utilities for the search pipeline."""

from __future__ import annotations

from typing import Any

from .similarity import (
    common_token_count,
    exact_match,
    jaccard_similarity,
    partial_ratio,
    safe_ratio,
    token_overlap_percent,
    token_set_ratio,
    token_sort_ratio,
    tokenize,
)

__all__ = [
    "ConfidenceScorer",
    "RankingEvaluator",
    "RankingFeatureBuilder",
    "RankingScoreCombiner",
    "MLRanker",
    "common_token_count",
    "exact_match",
    "jaccard_similarity",
    "partial_ratio",
    "safe_ratio",
    "token_overlap_percent",
    "token_set_ratio",
    "token_sort_ratio",
    "tokenize",
]


def __getattr__(name: str) -> Any:
    if name == "ConfidenceScorer":
        from .confidence_score import ConfidenceScorer

        return ConfidenceScorer
    if name == "RankingEvaluator":
        from .scorer import RankingEvaluator

        return RankingEvaluator
    if name == "RankingFeatureBuilder":
        from .feature_engineering import RankingFeatureBuilder

        return RankingFeatureBuilder
    if name == "RankingScoreCombiner":
        from .scorer import RankingScoreCombiner

        return RankingScoreCombiner
    if name == "MLRanker":
        from .ranker import MLRanker

        return MLRanker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
