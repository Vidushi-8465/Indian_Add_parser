"""Schema standardization and dataset merging."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from utils.string_utils import normalize_column_name


@dataclass
class StandardizationResult:
    """Outcome of mapping a dataset to the master schema."""

    dataframe: pd.DataFrame
    column_mapping: dict[str, str]
    unmapped_columns: list[str]


class SchemaStandardizer:
    """Map heterogeneous column names to the configured standard schema."""

    def __init__(
        self,
        standard_columns: list[str],
        column_aliases: dict[str, list[str]],
        dtype_rules: dict[str, list[str]] | None = None,
    ) -> None:
        self.standard_columns = [column for column in standard_columns if column != "source_file"]
        self.alias_lookup = self._build_alias_lookup(column_aliases)
        self.dtype_rules = dtype_rules or {}

    def standardize(self, dataframe: pd.DataFrame, source_file: str) -> StandardizationResult:
        column_mapping: dict[str, str] = {}
        unmapped_columns: list[str] = []
        renamed_frames: dict[str, pd.Series] = {}

        for original_column in dataframe.columns:
            original_name = str(original_column).strip()
            if original_name.startswith("Unnamed"):
                unmapped_columns.append(original_name)
                continue

            standard_name = self._resolve_standard_name(original_name)
            if standard_name is None:
                unmapped_columns.append(original_name)
                continue

            if standard_name in renamed_frames:
                existing = renamed_frames[standard_name]
                renamed_frames[standard_name] = existing.where(existing.notna() & existing.ne(""), dataframe[original_column])
            else:
                renamed_frames[standard_name] = dataframe[original_column]
                column_mapping[original_name] = standard_name

        standardized = pd.DataFrame(renamed_frames)
        for column in self.standard_columns:
            if column not in standardized.columns:
                standardized[column] = pd.NA

        standardized = standardized[self.standard_columns]
        standardized["source_file"] = source_file
        standardized = self._apply_dtype_rules(standardized)
        return StandardizationResult(
            dataframe=standardized,
            column_mapping=column_mapping,
            unmapped_columns=unmapped_columns,
        )

    def _resolve_standard_name(self, original_column: str) -> str | None:
        normalized = normalize_column_name(original_column)
        return self.alias_lookup.get(normalized)

    def _build_alias_lookup(self, column_aliases: dict[str, list[str]]) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for standard_name, aliases in column_aliases.items():
            lookup[normalize_column_name(standard_name)] = standard_name
            for alias in aliases:
                lookup[normalize_column_name(alias)] = standard_name
        return lookup

    def _apply_dtype_rules(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        typed = dataframe.copy()

        for column in self.dtype_rules.get("string_columns", []):
            if column in typed.columns:
                typed[column] = typed[column].apply(self._to_nullable_string)

        for column in self.dtype_rules.get("float_columns", []):
            if column in typed.columns:
                typed[column] = pd.to_numeric(typed[column], errors="coerce")

        for column in typed.columns:
            if column not in self.dtype_rules.get("float_columns", []):
                if column != "source_file" and typed[column].dtype != "object":
                    typed[column] = typed[column].apply(self._to_nullable_string)

        return typed

    @staticmethod
    def _to_nullable_string(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = str(value).strip()
        if text.lower() in {"", "nan", "none", "null"}:
            return pd.NA
        if text.endswith(".0") and text.replace(".0", "").isdigit():
            return text[:-2]
        return text


class DatasetMerger:
    """Merge standardized datasets into a single master dataframe."""

    def merge(self, dataframes: list[pd.DataFrame], standard_columns: list[str]) -> pd.DataFrame:
        if not dataframes:
            return pd.DataFrame(columns=standard_columns)

        aligned = [frame.reindex(columns=standard_columns) for frame in dataframes]
        return pd.concat(aligned, ignore_index=True, sort=False)
