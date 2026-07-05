"""Enforce final output dtypes before writing the cleaned dataset."""

from __future__ import annotations

from typing import Any

import pandas as pd


class DtypeEnforcer:
    """Cast columns to their expected output types."""

    DEFAULT_STRING_COLUMNS = [
        "full_address",
        "searchable_text",
        "address_hash",
    ]

    def enforce(self, dataframe: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
        enforced = dataframe.copy()

        string_columns = set(self.DEFAULT_STRING_COLUMNS)
        string_columns.update(config.get("string_columns", []))
        string_columns.update(config.get("admin_code_columns", []))
        string_columns.update(config.get("name_columns", []))

        for column in string_columns:
            if column not in enforced.columns:
                continue
            enforced[column] = enforced[column].map(self._to_string).astype("string")

        if "quality_score" in enforced.columns:
            enforced["quality_score"] = pd.to_numeric(enforced["quality_score"], errors="coerce").round(2)

        for column in ("latitude", "longitude"):
            if column not in enforced.columns:
                continue
            enforced[column] = enforced[column].map(self._to_string).astype("string")

        return enforced

    @staticmethod
    def _to_string(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null", "na", "n/a", "<na>"}:
            return pd.NA
        return text
