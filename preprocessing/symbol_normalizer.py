"""Normalize special symbols in address text fields."""

from __future__ import annotations

import re

import pandas as pd

from utils.regex_utils import DASH_BETWEEN_TOKENS_PATTERN


class SymbolNormalizer:
    """Clean punctuation patterns such as 'sector - 21' -> 'sector 21'."""

    SPECIAL_SYMBOL_PATTERN = re.compile(r"[^\w\s,./#&'-]", re.UNICODE)

    def normalize(self, dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        normalized = dataframe.copy()
        for column in columns:
            if column not in normalized.columns:
                continue
            normalized[column] = normalized[column].apply(self._normalize_cell)
        return normalized

    def _normalize_cell(self, value: object) -> object:
        if pd.isna(value):
            return pd.NA

        text = str(value).strip()
        text = DASH_BETWEEN_TOKENS_PATTERN.sub(" ", text)
        text = self.SPECIAL_SYMBOL_PATTERN.sub(" ", text)
        text = " ".join(text.split())
        return text if text else pd.NA
