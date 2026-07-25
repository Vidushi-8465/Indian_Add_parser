"""XGBoost-backed ML ranker with a fallback heuristic scorer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import pickle
from typing import Any, Sequence

import numpy as np

try:
    from xgboost import XGBRanker
except Exception:  # pragma: no cover - optional dependency fallback
    XGBRanker = None  # type: ignore[assignment]

from search.locality_aliases import locality_variants
from search.search_results import SearchCandidate, SearchEntities

from .confidence_score import ConfidenceScorer
from .feature_engineering import RankingFeatureBuilder, RankingFeatureVector
from .scorer import RankingScoreCombiner
from .similarity import exact_match, normalize_text, safe_ratio


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
        self.feature_names: list[str] = self.feature_builder.feature_names()
        # When a trained model is loaded, its feature order is fixed and must not
        # be recomputed per request, or inference columns would drift from training.
        self._features_locked: bool = False
        self.model: Any | None = self._load_model(self.artifact.model_path)

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

        if not self._features_locked:
            self.feature_names = self.feature_builder.feature_names(feature_rows)
        ranked_candidates: list[SearchCandidate] = []

        if self.model is None:
            model_scores = [None] * len(feature_rows)
        else:
            model_scores = self._predict_scores(feature_rows)

        has_entities = self._has_entity_signal(parsed_entities)
        for candidate, feature_row, model_score in zip(candidates, feature_rows, model_scores):
            exact_match_count = sum(
                int(value)
                for key, value in feature_row.values.items()
                if key.startswith("exact_")
            )
            entity_fit = self._entity_fit(parsed_entities, candidate, feature_row)
            bm25_score = candidate.bm25_score or candidate.score
            # Prefer entity-aware heuristic when the query has clear entities —
            # a weak/noisy ranking model must not demote the true best match.
            effective_model_score = None if has_entities else model_score
            final_score = self.score_combiner.combine(
                model_score=effective_model_score,
                bm25_score=bm25_score,
                exact_match_count=exact_match_count,
                quality_score=candidate.quality_score,
                entity_fit=entity_fit,
            )
            candidate.score = final_score
            candidate.confidence = self.confidence_scorer.score(
                model_score=effective_model_score,
                bm25_score=bm25_score,
                exact_match_count=exact_match_count,
                quality_score=candidate.quality_score,
                entity_fit=entity_fit,
            ).confidence
            ranked_candidates.append(candidate)

        # Confidence is the public ranking signal — keep the highest-confidence
        # candidate first so results[0] and best_match always agree.
        ranked_candidates.sort(
            key=lambda item: (item.confidence, item.score, item.bm25_score),
            reverse=True,
        )
        return ranked_candidates

    @staticmethod
    def _has_entity_signal(parsed_entities: SearchEntities) -> bool:
        return any(
            (
                parsed_entities.locality,
                parsed_entities.city,
                parsed_entities.building_name,
                parsed_entities.office_name,
                parsed_entities.road_name,
                parsed_entities.pincode,
                parsed_entities.district,
                parsed_entities.state,
            )
        )

    @classmethod
    def _locality_similarity(cls, query_locality: str | None, candidate_locality: str | None) -> float:
        if not query_locality or not candidate_locality:
            return 0.0
        ratios = [
            safe_ratio(variant, candidate_locality)
            for variant in locality_variants(query_locality)
        ]
        ratio = max(ratios) if ratios else 0.0
        prefix = cls._prefix_affinity(query_locality, candidate_locality)
        for variant in locality_variants(query_locality):
            prefix = max(prefix, cls._prefix_affinity(variant, candidate_locality))
        # Prefer real spelling variants (Hinjavadi) over shared suffixes (Shindewadi).
        return max(0.0, min(1.0, 0.55 * ratio + 0.45 * prefix))

    @staticmethod
    def _prefix_affinity(left: str | None, right: str | None) -> float:
        left_norm = normalize_text(left)
        right_norm = normalize_text(right)
        if not left_norm or not right_norm:
            return 0.0
        shared = 0
        for left_char, right_char in zip(left_norm, right_norm):
            if left_char != right_char:
                break
            shared += 1
        return shared / max(len(left_norm), len(right_norm))

    @classmethod
    def _entity_fit(
        cls,
        parsed_entities: SearchEntities,
        candidate: SearchCandidate,
        feature_row: RankingFeatureVector,
    ) -> float:
        """How well the candidate matches detected query entities (0–1)."""
        fit = 0.0
        locality_sim = 0.0

        if parsed_entities.locality:
            locality_sim = cls._locality_similarity(parsed_entities.locality, candidate.locality)
            # Also accept locality sitting in full_address when dedicated field is weak.
            address_sim = max(
                safe_ratio(variant, candidate.full_address)
                for variant in locality_variants(parsed_entities.locality)
            )
            locality_sim = max(locality_sim, 0.85 * address_sim if address_sim >= 0.5 else locality_sim)
            fit += 0.60 * locality_sim
            if locality_sim >= 0.88:
                fit += 0.15

        if parsed_entities.office_name:
            office_sim = max(
                safe_ratio(parsed_entities.office_name, candidate.office_name),
                safe_ratio(parsed_entities.office_name, candidate.building_name),
                safe_ratio(parsed_entities.office_name, candidate.full_address),
            )
            fit += 0.55 * office_sim
            if office_sim >= 0.85:
                fit += 0.15

        if parsed_entities.city:
            city_q = parsed_entities.city
            city_variants = locality_variants(city_q) or [normalize_text(city_q)]
            city_hit = any(
                exact_match(variant, candidate.city_name)
                or exact_match(variant, candidate.district_name)
                for variant in city_variants
            )
            city_ratio = max(
                max(safe_ratio(variant, candidate.city_name) for variant in city_variants),
                max(safe_ratio(variant, candidate.district_name) for variant in city_variants),
            )
            # City alone must not crown a weak locality match like Shindewadi for Hinjewadi.
            city_weight = 0.35 if (not parsed_entities.locality or locality_sim >= 0.72) else 0.08
            fit += city_weight if city_hit else city_weight * city_ratio

        if parsed_entities.building_name:
            building_ratio = max(
                float(feature_row.values.get("building_name__building_name__ratio", 0.0)),
                safe_ratio(parsed_entities.building_name, candidate.building_name),
                safe_ratio(parsed_entities.building_name, candidate.full_address),
            )
            fit += 0.25 * building_ratio

        if parsed_entities.pincode and exact_match(parsed_entities.pincode, candidate.pincode):
            fit += 0.25

        if parsed_entities.road_name:
            road_sim = max(
                safe_ratio(parsed_entities.road_name, candidate.road_name),
                safe_ratio(parsed_entities.road_name, candidate.full_address),
            )
            fit += 0.15 * road_sim

        return max(0.0, min(1.0, fit))

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

        derived_names = self._derive_feature_names(feature_rows)
        if derived_names:
            self.feature_names = derived_names
            self._features_locked = True

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
        # Persist the training feature order so inference builds identical columns.
        if self.feature_names:
            self._feature_sidecar_path(path).write_text(
                json.dumps(self.feature_names), encoding="utf-8"
            )

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

        self._load_feature_names(path)

        if XGBRanker is not None and path.suffix.lower() in {".json", ".ubj", ".bst"}:
            ranker = XGBRanker()
            ranker.load_model(str(path))
            return ranker

        with path.open("rb") as handle:
            return pickle.load(handle)

    def _load_feature_names(self, model_path: Path) -> None:
        sidecar = self._feature_sidecar_path(model_path)
        if not sidecar.exists():
            return
        try:
            names = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(names, list) and names:
            self.feature_names = [str(name) for name in names]
            self._features_locked = True

    @staticmethod
    def _feature_sidecar_path(model_path: Path) -> Path:
        return model_path.with_suffix(model_path.suffix + ".features.json")

    @staticmethod
    def _derive_feature_names(feature_rows: Sequence[Any]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for row in feature_rows:
            values = row.values if hasattr(row, "values") and isinstance(getattr(row, "values"), dict) else row
            if not isinstance(values, dict):
                return []
            for name in values:
                if name not in seen:
                    seen.add(name)
                    names.append(str(name))
        return names

    @staticmethod
    def _default_model_path() -> str:
        env_path = os.getenv("RANKING_MODEL_PATH")
        if env_path:
            return env_path
        return str(Path(__file__).resolve().parents[1] / "models" / "ranking_model.json")
