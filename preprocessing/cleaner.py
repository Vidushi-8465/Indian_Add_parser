"""Remove empty rows/columns and clean invalid cell characters."""

from __future__ import annotations

import pandas as pd

from utils.regex_utils import EXTRA_COMMA_PATTERN, INVISIBLE_UNICODE_PATTERN


class DataCleaner:
    """Structural cleanup for tabular address data."""

    def remove_empty_rows(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        before = len(dataframe.index)
        cleaned = dataframe.dropna(how="all")
        blank_mask = cleaned.apply(
            lambda row: row.astype(str).str.strip().isin(["", "nan", "None", "<NA>"]).all(),
            axis=1,
        )
        cleaned = cleaned.loc[~blank_mask].reset_index(drop=True)
        removed = before - len(cleaned.index)
        return cleaned, removed

    def remove_empty_columns(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        before = len(dataframe.columns)
        non_empty_columns = [
            column
            for column in dataframe.columns
            if not dataframe[column].isna().all()
            and not dataframe[column].astype(str).str.strip().isin(["", "nan", "None", "<NA>"]).all()
        ]
        cleaned = dataframe[non_empty_columns].copy()
        removed = before - len(cleaned.columns)
        return cleaned, removed

    def clean_invalid_characters(self, dataframe: pd.DataFrame, string_columns: list[str]) -> pd.DataFrame:
        cleaned = dataframe.copy()
        for column in string_columns:
            if column not in cleaned.columns:
                continue
            cleaned[column] = cleaned[column].apply(self._clean_cell)
        return cleaned

    @staticmethod
    def _clean_cell(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = str(value)
        text = INVISIBLE_UNICODE_PATTERN.sub("", text)
        text = EXTRA_COMMA_PATTERN.sub(",", text)
        text = text.strip()
        text = " ".join(text.split())
        return text if text else pd.NA
