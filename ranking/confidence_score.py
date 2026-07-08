"""Confidence scoring for ML reranked search results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConfidenceScoreBreakdown:
    confidence: float
    label: str


class ConfidenceScorer:
    """Blend model, BM25, exact match, and quality signals into a confidence score."""

    def score(
        self,
        *,
        model_score: float | None,
        bm25_score: float | None,
        exact_match_count: float | int = 0,
        quality_score: float | None = None,
    ) -> ConfidenceScoreBreakdown:
        normalized_model = self._sigmoid(model_score) if model_score is not None else 0.0
        normalized_bm25 = self._normalize_bm25(bm25_score)
        normalized_quality = self._normalize_quality(quality_score)
        exact_bonus = min(1.0, float(exact_match_count) / 6.0)

        confidence = (
            0.55 * normalized_model
            + 0.20 * normalized_bm25
            + 0.15 * exact_bonus
            + 0.10 * normalized_quality
        )
        confidence = round(max(0.0, min(0.99, confidence)), 4)
        return ConfidenceScoreBreakdown(confidence=confidence, label=self._label(confidence))

    @staticmethod
    def _sigmoid(value: float) -> float:
        import math

        return float(1.0 / (1.0 + math.exp(-float(value))))

    @staticmethod
    def _normalize_bm25(value: float | None) -> float:
        if value in (None, 0):
            return 0.0
        return float(max(0.0, min(1.0, float(value) / (float(value) + 5.0))))

    @staticmethod
    def _normalize_quality(value: float | None) -> float:
        if value in (None, ""):
            return 0.0
        try:
            return float(max(0.0, min(1.0, float(value) / 100.0)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _label(confidence: float) -> str:
        if confidence > 0.95:
            return "exact_match"
        if confidence >= 0.80:
            return "high"
        if confidence >= 0.60:
            return "medium"
        return "low"
