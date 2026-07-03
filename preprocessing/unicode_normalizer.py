"""Unicode normalization for text fields."""

from __future__ import annotations

import unicodedata

import pandas as pd

from utils.regex_utils import INVISIBLE_UNICODE_PATTERN


class UnicodeNormalizer:
    """Normalize unicode representations and strip invisible characters."""

    def normalize(self, dataframe: pd.DataFrame, string_columns: list[str]) -> pd.DataFrame:
        normalized = dataframe.copy()
        for column in string_columns:
            if column not in normalized.columns:
                continue
            normalized[column] = normalized[column].apply(self._normalize_cell)
        return normalized

    @staticmethod
    def _normalize_cell(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = unicodedata.normalize("NFKC", str(value))
        text = INVISIBLE_UNICODE_PATTERN.sub("", text)
        text = text.strip()
        return text if text else pd.NA
