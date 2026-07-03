"""Schema standardization and dataset merging for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from rapidfuzz import fuzz

from utils.string_utils import is_subdistrict_column, normalize_column_name

FUZZY_MATCH_THRESHOLD = 88


@dataclass
class ColumnMatch:
    """How a source column was mapped to the standard schema."""

    original_column: str
    standard_column: str
    confidence: float
    method: str


@dataclass
class StandardizationResult:
    """Output after schema standardization."""

    dataframe: pd.DataFrame
    column_mapping: dict[str, str]
    unmapped_columns: list[str]
    mapping_report: list[ColumnMatch] = field(default_factory=list)
    mapping_confidence: float = 0.0


class SchemaStandardizer:
    """Map heterogeneous schemas into one canonical schema."""

    def __init__(
        self,
        standard_columns: list[str],
        column_aliases: dict[str, list[str]],
        dtype_rules: dict[str, list[str]] | None = None,
    ) -> None:
        self.standard_columns = [column for column in standard_columns if column != "source_file"]
        self.column_aliases = column_aliases
        self.alias_lookup = self._build_alias_lookup(column_aliases)
        self.dtype_rules = dtype_rules or {}

    def standardize(self, dataframe: pd.DataFrame, source_file: str) -> StandardizationResult:
        column_mapping: dict[str, str] = {}
        unmapped_columns: list[str] = []
        mapping_report: list[ColumnMatch] = []
        renamed_frames: dict[str, pd.Series] = {}
        total_confidence = 0.0
        mapped_columns = 0

        for original_column in dataframe.columns:
            original_name = str(original_column).strip()
            if not original_name or original_name.startswith("Unnamed"):
                unmapped_columns.append(original_name)
                continue

            standard_name, confidence, method = self._resolve_standard_name(original_name)
            if standard_name is None:
                unmapped_columns.append(original_name)
                continue

            mapping_report.append(
                ColumnMatch(
                    original_column=original_name,
                    standard_column=standard_name,
                    confidence=confidence,
                    method=method,
                )
            )
            total_confidence += confidence
            mapped_columns += 1
            column_mapping[original_name] = standard_name

            if standard_name in renamed_frames:
                renamed_frames[standard_name] = self._merge_columns(
                    renamed_frames[standard_name],
                    dataframe[original_column],
                )
            else:
                renamed_frames[standard_name] = dataframe[original_column]

        standardized = pd.DataFrame(renamed_frames)
        for column in self.standard_columns:
            if column not in standardized.columns:
                standardized[column] = pd.NA

        standardized = standardized[self.standard_columns]
        standardized["source_file"] = source_file
        standardized = self._apply_dtype_rules(standardized)

        mapping_confidence = round(total_confidence / mapped_columns, 2) if mapped_columns else 0.0
        return StandardizationResult(
            dataframe=standardized,
            column_mapping=column_mapping,
            unmapped_columns=unmapped_columns,
            mapping_report=mapping_report,
            mapping_confidence=mapping_confidence,
        )

    def _resolve_standard_name(self, original_column: str) -> tuple[str | None, float, str]:
        normalized = normalize_column_name(original_column)

        if normalized in self.alias_lookup:
            return self.alias_lookup[normalized], 100.0, "exact"

        best_score = 0.0
        best_column: str | None = None
        for alias, standard in self.alias_lookup.items():
            if self._is_incompatible_fuzzy_match(normalized, standard):
                continue

            score = fuzz.ratio(normalized, alias)
            if score > best_score:
                best_score = score
                best_column = standard

        if best_column is not None and best_score >= FUZZY_MATCH_THRESHOLD:
            return best_column, float(best_score), "fuzzy"

        return None, 0.0, "unmapped"

    @staticmethod
    def _is_incompatible_fuzzy_match(normalized_column: str, standard_column: str) -> bool:
        """Prevent fuzzy matches that collapse distinct administrative levels."""
        column_is_subdistrict = is_subdistrict_column(normalized_column)
        standard_is_subdistrict = standard_column.startswith("subdistrict_")
        standard_is_district = standard_column.startswith("district_")

        if column_is_subdistrict and standard_is_district and not standard_is_subdistrict:
            return True
        if not column_is_subdistrict and standard_is_subdistrict:
            return True
        return False

    def _merge_columns(self, existing: pd.Series, incoming: pd.Series) -> pd.Series:
        merged = existing.copy()
        for idx in merged.index:
            left = merged.iloc[idx]
            right = incoming.iloc[idx]

            if pd.isna(left):
                merged.iloc[idx] = right
                continue
            if pd.isna(right):
                continue

            left_text = str(left).strip()
            right_text = str(right).strip()
            if len(right_text) > len(left_text):
                merged.iloc[idx] = right

        return merged

    def _apply_dtype_rules(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        typed = dataframe.copy()
        float_columns = set(self.dtype_rules.get("float_columns", []))
        string_columns = set(self.dtype_rules.get("string_columns", []))

        for column in typed.columns:
            if column == "source_file":
                continue
            if column in float_columns:
                typed[column] = pd.to_numeric(typed[column], errors="coerce")
            elif column in string_columns or typed[column].dtype != "object":
                typed[column] = typed[column].apply(self._to_nullable_string)

        return typed

    def _build_alias_lookup(self, column_aliases: dict[str, list[str]]) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for standard_name, aliases in column_aliases.items():
            lookup[normalize_column_name(standard_name)] = standard_name
            for alias in aliases:
                lookup[normalize_column_name(alias)] = standard_name
        return lookup

    @staticmethod
    def _to_nullable_string(value: object) -> object:
        if pd.isna(value):
            return pd.NA

        text = str(value).strip()
        if not text:
            return pd.NA
        if text.lower() in {"nan", "none", "null", "na", "n/a", "-", "--"}:
            return pd.NA

        text = " ".join(text.split())
        if text.endswith(".0"):
            digits = text[:-2]
            if digits.isdigit():
                return digits
        return text


class DatasetMerger:
    """Merge standardized datasets into a single master dataframe."""

    def __init__(self) -> None:
        self.stats = {
            "datasets": 0,
            "rows_before_merge": 0,
            "rows_after_merge": 0,
        }

    def merge(self, dataframes: list[pd.DataFrame], standard_columns: list[str]) -> pd.DataFrame:
        if not dataframes:
            return pd.DataFrame(columns=standard_columns)

        self.stats["datasets"] = len(dataframes)
        self.stats["rows_before_merge"] = sum(len(frame) for frame in dataframes)

        aligned = [frame.reindex(columns=standard_columns) for frame in dataframes]
        merged = pd.concat(aligned, ignore_index=True, sort=False)

        self.stats["rows_after_merge"] = len(merged.index)
        return merged

    def get_statistics(self) -> dict[str, int]:
        return self.stats
