"""Dataset-level statistics for preprocessing."""

from __future__ import annotations

from typing import Any

import pandas as pd


class DatasetStatistics:
    """Compute summary statistics over a processed dataframe."""

    def compute(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "total_rows": int(len(dataframe.index)),
            "total_columns": int(len(dataframe.columns)),
            "duplicate_address_hashes": self._duplicate_hash_count(dataframe),
            "quality_score": self._quality_summary(dataframe),
            "null_percentages": self._null_percentages(dataframe),
            "unique_counts": self._unique_counts(dataframe),
            "pincode_coverage": self._field_coverage(dataframe, "pincode"),
            "coordinate_coverage": {
                "latitude": self._field_coverage(dataframe, "latitude"),
                "longitude": self._field_coverage(dataframe, "longitude"),
            },
        }
        return stats

    @staticmethod
    def _duplicate_hash_count(dataframe: pd.DataFrame) -> int:
        if "address_hash" not in dataframe.columns:
            return 0
        hashes = dataframe["address_hash"].dropna()
        if hashes.empty:
            return 0
        return int(hashes.duplicated(keep=False).sum())

    @staticmethod
    def _quality_summary(dataframe: pd.DataFrame) -> dict[str, float | int]:
        if "quality_score" not in dataframe.columns:
            return {"available": False}
        scores = pd.to_numeric(dataframe["quality_score"], errors="coerce").dropna()
        if scores.empty:
            return {"available": False}
        return {
            "available": True,
            "min": float(scores.min()),
            "max": float(scores.max()),
            "mean": round(float(scores.mean()), 2),
            "median": round(float(scores.median()), 2),
            "rows_below_50": int((scores < 50).sum()),
        }

    @staticmethod
    def _null_percentages(dataframe: pd.DataFrame) -> dict[str, float]:
        percentages: dict[str, float] = {}
        total = max(len(dataframe.index), 1)
        for column in dataframe.columns:
            null_count = int(dataframe[column].isna().sum())
            if dataframe[column].dtype == object:
                blank_count = int(
                    dataframe[column].astype(str).str.strip().isin(["", "nan", "None", "<NA>"]).sum()
                )
                null_count = max(null_count, blank_count)
            percentages[column] = round((null_count / total) * 100, 2)
        return percentages

    @staticmethod
    def _unique_counts(dataframe: pd.DataFrame) -> dict[str, int]:
        fields = [
            "state_name",
            "district_name",
            "city_name",
            "locality",
            "pincode",
            "address_hash",
        ]
        return {
            field: int(dataframe[field].nunique(dropna=True))
            for field in fields
            if field in dataframe.columns
        }

    @staticmethod
    def _field_coverage(dataframe: pd.DataFrame, column: str) -> dict[str, int | float]:
        if column not in dataframe.columns:
            return {"present": 0, "percentage": 0.0}
        total = max(len(dataframe.index), 1)
        present = int(dataframe[column].notna().sum())
        return {
            "present": present,
            "percentage": round((present / total) * 100, 2),
        }
