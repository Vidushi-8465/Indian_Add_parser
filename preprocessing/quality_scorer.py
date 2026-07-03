"""Compute per-row data quality scores."""

from __future__ import annotations

import pandas as pd

_NULL_LIKE = {"nan", "none", "null", "na", "n/a"}


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

        earned = pd.Series(0.0, index=scored.index)
        for field, weight in self.field_weights.items():
            if field not in scored.columns:
                continue
            column = scored[field]
            valid = column.notna()
            text = column.astype(str).str.strip()
            valid &= ~text.str.lower().isin(_NULL_LIKE) & (text != "")
            earned += valid.astype(float) * weight

        scored["quality_score"] = (earned / total_weight * 100).round(2)
        return scored
