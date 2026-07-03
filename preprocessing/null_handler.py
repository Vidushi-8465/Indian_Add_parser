"""Null normalization and hierarchical value filling."""

from __future__ import annotations

import pandas as pd


class NullHandler:
    """Convert null-like tokens to pd.NA and fill missing values where possible."""

    def __init__(self, null_like_values: list[str] | None = None) -> None:
        defaults = {"", "null", "none", "na", "n/a", "nan", "-", "--", "."}
        configured = {str(value).strip().lower() for value in (null_like_values or [])}
        self.null_like_values = defaults | configured

    def normalize_nulls(self, dataframe: pd.DataFrame, string_columns: list[str]) -> pd.DataFrame:
        normalized = dataframe.copy()
        for column in string_columns:
            if column not in normalized.columns:
                continue
            normalized[column] = normalized[column].apply(self._to_na)
        return normalized

    def fill_missing_values(
        self,
        dataframe: pd.DataFrame,
        hierarchy_mappings: dict[str, str],
    ) -> tuple[pd.DataFrame, dict[str, int]]:
        filled = dataframe.copy()
        fill_counts: dict[str, int] = {}

        for code_column, name_column in hierarchy_mappings.items():
            if code_column not in filled.columns or name_column not in filled.columns:
                continue

            lookup = self._build_code_name_lookup(filled[code_column], filled[name_column])
            if not lookup:
                continue

            missing_mask = filled[name_column].isna() & filled[code_column].notna()
            if not missing_mask.any():
                continue

            filled.loc[missing_mask, name_column] = filled.loc[missing_mask, code_column].map(lookup)
            fill_counts[name_column] = int(missing_mask.sum())

        return filled, fill_counts

    def _to_na(self, value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = str(value).strip()
        if text.lower() in self.null_like_values:
            return pd.NA
        return value

    @staticmethod
    def _build_code_name_lookup(codes: pd.Series, names: pd.Series) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for code, name in zip(codes, names, strict=False):
            if pd.isna(code) or pd.isna(name):
                continue
            code_key = str(code).strip()
            name_value = str(name).strip()
            if code_key and name_value and code_key not in lookup:
                lookup[code_key] = name_value
        return lookup
