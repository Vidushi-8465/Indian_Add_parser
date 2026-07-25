"""Ranking score aggregation and evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import math


@dataclass(slots=True)
class RankingScoreCombiner:
    """Fallback score combiner used when an ML model is unavailable."""

    model_weight: float = 0.45
    bm25_weight: float = 0.15
    exact_match_weight: float = 0.30
    quality_weight: float = 0.10

    def combine(
        self,
        *,
        model_score: float | None,
        bm25_score: float | None,
        exact_match_count: float | int = 0,
        quality_score: float | None = None,
        entity_fit: float = 0.0,
    ) -> float:
        normalized_model = self._sigmoid(model_score) if model_score is not None else 0.0
        normalized_bm25 = self._normalize_bm25(bm25_score)
        normalized_quality = self._normalize_quality(quality_score)
        exact_bonus = min(1.0, float(exact_match_count) / 2.0)
        fit = max(0.0, min(1.0, float(entity_fit)))

        if model_score is None:
            score = (
                0.10 * normalized_bm25
                + 0.20 * exact_bonus
                + 0.55 * fit
                + 0.15 * normalized_quality
            )
        else:
            score = (
                0.30 * normalized_model
                + 0.05 * normalized_bm25
                + 0.20 * exact_bonus
                + 0.35 * fit
                + 0.10 * normalized_quality
            )
        return round(max(0.0, min(1.0, score)), 6)

    @staticmethod
    def _sigmoid(value: float) -> float:
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


class RankingEvaluator:
    """Compute standard ranking metrics for offline evaluation."""

    @staticmethod
    def ndcg_at_k(labels: Sequence[float], scores: Sequence[float], k: int = 10) -> float:
        ordered_labels = RankingEvaluator._ordered_labels(labels, scores, k)
        ideal_labels = sorted(labels, reverse=True)[:k]
        return RankingEvaluator._dcg(ordered_labels) / (RankingEvaluator._dcg(ideal_labels) or 1.0)

    @staticmethod
    def mrr(labels: Sequence[float], scores: Sequence[float]) -> float:
        ordered = RankingEvaluator._ordered_labels(labels, scores, len(labels))
        for index, label in enumerate(ordered, start=1):
            if label > 0:
                return 1.0 / index
        return 0.0

    @staticmethod
    def precision_at_k(labels: Sequence[float], scores: Sequence[float], k: int = 10) -> float:
        ordered = RankingEvaluator._ordered_labels(labels, scores, k)
        if not ordered:
            return 0.0
        relevant = sum(1 for label in ordered[:k] if label > 0)
        return relevant / min(k, len(labels))

    @staticmethod
    def recall_at_k(labels: Sequence[float], scores: Sequence[float], k: int = 100) -> float:
        ordered = RankingEvaluator._ordered_labels(labels, scores, k)
        total_relevant = sum(1 for label in labels if label > 0)
        if total_relevant == 0:
            return 0.0
        relevant = sum(1 for label in ordered[:k] if label > 0)
        return relevant / total_relevant

    @staticmethod
    def top_k_accuracy(labels: Sequence[float], scores: Sequence[float], k: int = 1) -> float:
        ordered = RankingEvaluator._ordered_labels(labels, scores, k)
        return 1.0 if any(label > 0 for label in ordered[:k]) else 0.0

    @staticmethod
    def evaluate(labels: Sequence[float], scores: Sequence[float]) -> dict[str, float]:
        return {
            "ndcg@10": RankingEvaluator.ndcg_at_k(labels, scores, k=10),
            "mrr": RankingEvaluator.mrr(labels, scores),
            "precision@10": RankingEvaluator.precision_at_k(labels, scores, k=10),
            "recall@100": RankingEvaluator.recall_at_k(labels, scores, k=100),
            "top1_accuracy": RankingEvaluator.top_k_accuracy(labels, scores, k=1),
            "top5_accuracy": RankingEvaluator.top_k_accuracy(labels, scores, k=5),
        }

    @staticmethod
    def _ordered_labels(labels: Sequence[float], scores: Sequence[float], k: int) -> list[float]:
        paired = sorted(zip(scores, labels), key=lambda item: item[0], reverse=True)
        return [label for _, label in paired[:k]]

    @staticmethod
    def _dcg(labels: Iterable[float]) -> float:
        total = 0.0
        for index, label in enumerate(labels, start=1):
            gain = (2.0**float(label) - 1.0) / math.log2(index + 1)
            total += gain
        return total
