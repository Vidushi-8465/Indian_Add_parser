"""XGBoost-backed ML ranker with a fallback heuristic scorer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import pickle
from typing import Any, Sequence

import numpy as np

try:
    from xgboost import XGBRanker
except Exception:  # pragma: no cover - optional dependency fallback
    XGBRanker = None  # type: ignore[assignment]

from search.search_results import SearchCandidate, SearchEntities

from .confidence_score import ConfidenceScorer
from .feature_engineering import RankingFeatureBuilder, RankingFeatureVector
from .scorer import RankingScoreCombiner


@dataclass(slots=True)
class RankingModelArtifact:
    model_path: str | None = None
    feature_names: list[str] | None = None


class MLRanker:
    """Rank the top ES candidates with an ML model when available."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        feature_builder: RankingFeatureBuilder | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        score_combiner: RankingScoreCombiner | None = None,
    ) -> None:
        self.feature_builder = feature_builder or RankingFeatureBuilder()
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.score_combiner = score_combiner or RankingScoreCombiner()
        self.artifact = RankingModelArtifact(model_path=str(model_path) if model_path else self._default_model_path())
        self.model: Any | None = self._load_model(self.artifact.model_path)
        self.feature_names: list[str] = self.feature_builder.feature_names()

    def rank_candidates(
        self,
        query: str | None,
        parsed_entities: SearchEntities,
        candidates: list[SearchCandidate],
        *,
        query_lat: float | None = None,
        query_lon: float | None = None,
    ) -> list[SearchCandidate]:
        if not candidates:
            return []

        feature_rows: list[RankingFeatureVector] = []
        for position, candidate in enumerate(candidates, start=1):
            candidate.es_rank = candidate.es_rank or position
            candidate.retrieval_position = candidate.retrieval_position or position
            feature_rows.append(
                self.feature_builder.build_feature_row(
                    query,
                    parsed_entities,
                    candidate,
                    candidate_rank=position,
                    retrieval_position=position,
                    query_lat=query_lat,
                    query_lon=query_lon,
                )
            )

        self.feature_names = self.feature_builder.feature_names(feature_rows)
        ranked_candidates: list[SearchCandidate] = []

        if self.model is None:
            model_scores = [None] * len(feature_rows)
        else:
            model_scores = self._predict_scores(feature_rows)

        for candidate, feature_row, model_score in zip(candidates, feature_rows, model_scores):
            exact_match_count = sum(
                int(value)
                for key, value in feature_row.values.items()
                if key.startswith("exact_")
            )
            bm25_score = candidate.bm25_score or candidate.score
            final_score = self.score_combiner.combine(
                model_score=model_score,
                bm25_score=bm25_score,
                exact_match_count=exact_match_count,
                quality_score=candidate.quality_score,
            )
            candidate.score = final_score
            candidate.confidence = self.confidence_scorer.score(
                model_score=model_score,
                bm25_score=bm25_score,
                exact_match_count=exact_match_count,
                quality_score=candidate.quality_score,
            ).confidence
            ranked_candidates.append(candidate)

        ranked_candidates.sort(key=lambda item: (item.score, item.confidence, item.bm25_score), reverse=True)
        return ranked_candidates

    def fit(
        self,
        feature_rows: Sequence[Sequence[float] | dict[str, float]],
        labels: Sequence[float],
        group: Sequence[int] | None = None,
        *,
        model_path: str | Path | None = None,
    ) -> Any:
        if XGBRanker is None:
            raise RuntimeError("xgboost is required to train the ranking model.")

        matrix = self._to_matrix(feature_rows)
        ranker = XGBRanker(
            objective="rank:pairwise",
            learning_rate=0.1,
            n_estimators=200,
            max_depth=6,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        fit_kwargs: dict[str, Any] = {"X": matrix, "y": np.asarray(labels, dtype=float)}
        if group is not None:
            fit_kwargs["group"] = np.asarray(group, dtype=int)
        ranker.fit(**fit_kwargs)
        self.model = ranker

        if model_path is not None:
            self.save(model_path)

        return ranker

    def save(self, model_path: str | Path | None = None) -> None:
        path = Path(model_path or self.artifact.model_path or self._default_model_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(self.model, "save_model"):
            self.model.save_model(str(path))
        else:
            with path.open("wb") as handle:
                pickle.dump(self.model, handle)

    def predict(self, feature_rows: Sequence[Sequence[float] | dict[str, float]]) -> list[float]:
        if not feature_rows:
            return []
        rows: list[RankingFeatureVector] = []
        for row in feature_rows:
            if isinstance(row, dict):
                rows.append(RankingFeatureVector(values={key: float(value) for key, value in row.items()}))
            else:
                rows.append(RankingFeatureVector(values={str(index): float(value) for index, value in enumerate(row)}))
        return self._predict_scores(rows)

    def _predict_scores(self, feature_rows: Sequence[RankingFeatureVector]) -> list[float]:
        if not feature_rows:
            return []

        if self.model is None:
            return [None for _ in feature_rows]

        matrix = self._to_matrix(feature_rows)
        if hasattr(self.model, "predict"):
            try:
                predictions = self.model.predict(matrix)
                return [float(value) for value in np.asarray(predictions).tolist()]
            except Exception:
                pass

        return [
            self.score_combiner.combine(
                model_score=None,
                bm25_score=row.values.get("candidate_bm25_score"),
                exact_match_count=sum(int(value) for key, value in row.values.items() if key.startswith("exact_")),
                quality_score=row.values.get("candidate_quality_score"),
            )
            for row in feature_rows
        ]

    def _to_matrix(self, feature_rows: Sequence[Sequence[float] | dict[str, float] | RankingFeatureVector]) -> np.ndarray:
        rows: list[list[float]] = []
        feature_names = self.feature_names or self.feature_builder.feature_names()
        for row in feature_rows:
            if isinstance(row, RankingFeatureVector):
                rows.append(row.as_ordered_list(feature_names))
            elif isinstance(row, dict):
                rows.append([float(row.get(name, 0.0)) for name in feature_names])
            else:
                rows.append([float(value) for value in row])
        return np.asarray(rows, dtype=float)

    def _load_model(self, model_path: str | None) -> Any | None:
        if not model_path:
            return None

        path = Path(model_path)
        if not path.exists():
            return None

        if XGBRanker is not None and path.suffix.lower() in {".json", ".ubj", ".bst"}:
            ranker = XGBRanker()
            ranker.load_model(str(path))
            return ranker

        with path.open("rb") as handle:
            return pickle.load(handle)

    @staticmethod
    def _default_model_path() -> str:
        env_path = os.getenv("RANKING_MODEL_PATH")
        if env_path:
            return env_path
        return str(Path(__file__).resolve().parents[1] / "models" / "ranking_model.json")
