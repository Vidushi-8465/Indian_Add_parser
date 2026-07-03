"""Compute per-row data quality scores."""

from __future__ import annotations

import pandas as pd


class QualityScorer:
    """Score each row based on completeness of key address fields."""

    DEFAULT_WEIGHTS = {
        "building_name": 10,
        "road_name": 10,
        "locality": 15,
        "city_name": 15,
        "district_name": 15,
        "state_name": 15,
        "pincode": 10,
        "latitude": 5,
        "longitude": 5,
    }

    def __init__(self, field_weights: dict[str, float] | None = None) -> None:
        self.field_weights = field_weights or self.DEFAULT_WEIGHTS

    def score(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        scored = dataframe.copy()
        total_weight = sum(
            weight for field, weight in self.field_weights.items() if field in scored.columns
        )
        if total_weight == 0:
            scored["quality_score"] = 0.0
            return scored

        scored["quality_score"] = scored.apply(
            lambda row: self._score_row(row, total_weight),
            axis=1,
        )
        return scored

    def _score_row(self, row: pd.Series, total_weight: float) -> float:
        earned = 0.0
        for field, weight in self.field_weights.items():
            if field not in row.index:
                continue
            value = row[field]
            if pd.isna(value):
                continue
            text = str(value).strip()
            if text and text.lower() not in {"nan", "none", "null", "na", "n/a"}:
                earned += weight
        return round((earned / total_weight) * 100, 2)
