"""String normalization, geographic standardization, and field validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from utils.file_utils import resolve_project_path
from utils.regex_utils import PINCODE_PATTERN
from utils.string_utils import coerce_identifier_string


class AddressNormalizer:
    """Normalize strings, geographic names, and validated numeric fields."""

    def __init__(self) -> None:
        self.logger = logger.bind(module="preprocessing.normalizer")

    def normalize_strings(
        self,
        dataframe: pd.DataFrame,
        name_columns: list[str],
    ) -> pd.DataFrame:
        normalized = dataframe.copy()
        for column in name_columns:
            if column not in normalized.columns:
                continue
            normalized[column] = normalized[column].apply(self._normalize_name_cell)
        return normalized

    def standardize_geographic_names(
        self,
        dataframe: pd.DataFrame,
        columns: list[str],
        hierarchy_paths: dict[str, str] | None = None,
    ) -> pd.DataFrame:
        standardized = dataframe.copy()
        hierarchy_paths = hierarchy_paths or {}

        for column in columns:
            if column not in standardized.columns:
                continue

            canonical_map = self._load_hierarchy_map(hierarchy_paths.get(column))
            if not canonical_map:
                canonical_map = self._build_canonical_map(standardized[column])

            keys = standardized[column].map(self._normalize_key)
            mapped = keys.map(canonical_map)
            missing = mapped.isna() & keys.ne("") & standardized[column].notna()
            if missing.any():
                mapped.loc[missing] = standardized.loc[missing, column].map(
                    lambda value: self.title_case_words(str(value).strip())
                )
            standardized[column] = mapped
            standardized.loc[keys == "", column] = pd.NA
        return standardized

    def normalize_admin_codes(
        self,
        dataframe: pd.DataFrame,
        columns: list[str],
    ) -> pd.DataFrame:
        """Cast pincode and administrative code columns to clean string values."""
        normalized = dataframe.copy()
        for column in columns:
            if column not in normalized.columns:
                continue
            normalized[column] = normalized[column].map(coerce_identifier_string).astype("string")
        return normalized

    def validate_pincode(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        if "pincode" not in dataframe.columns:
            return dataframe, 0

        validated = dataframe.copy()
        raw = validated["pincode"].map(coerce_identifier_string)
        present = raw.notna() & (raw.astype(str).str.strip() != "")
        valid = present & raw.astype(str).str.fullmatch(PINCODE_PATTERN.pattern)
        invalid_count = int((present & ~valid).sum())

        validated["pincode"] = pd.NA
        validated.loc[present & valid, "pincode"] = raw.loc[present & valid].astype(str)
        validated["pincode"] = validated["pincode"].astype("string")
        return validated, invalid_count

    def validate_coordinates(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        validated = dataframe.copy()
        invalid_counts = {"latitude": 0, "longitude": 0}

        if "latitude" in validated.columns:
            validated, invalid_counts["latitude"] = self._validate_numeric_range(
                validated,
                column="latitude",
                minimum=-90.0,
                maximum=90.0,
            )
        if "longitude" in validated.columns:
            validated, invalid_counts["longitude"] = self._validate_numeric_range(
                validated,
                column="longitude",
                minimum=-180.0,
                maximum=180.0,
            )
        return validated, invalid_counts

    def _validate_numeric_range(
        self,
        dataframe: pd.DataFrame,
        column: str,
        minimum: float,
        maximum: float,
    ) -> tuple[pd.DataFrame, int]:
        validated = dataframe.copy()
        raw = validated[column]
        present = raw.notna() & (raw.astype(str).str.strip() != "")
        numeric = pd.to_numeric(raw, errors="coerce")
        valid = present & numeric.notna() & (numeric >= minimum) & (numeric <= maximum)
        invalid_count = int((present & ~valid).sum())

        if invalid_count:
            self.logger.warning(
                "Found {} invalid {} values (allowed {} to {}); set to null",
                invalid_count,
                column,
                minimum,
                maximum,
            )

        validated.loc[present & valid, column] = raw[present & valid].astype(str).str.strip()
        validated.loc[present & ~valid, column] = pd.NA
        return validated, invalid_count

    @staticmethod
    def _normalize_name_cell(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        text = str(value).strip()
        text = " ".join(text.split())
        return AddressNormalizer.title_case_words(text)

    @staticmethod
    def title_case_words(text: str) -> str:
        return " ".join(word[:1].upper() + word[1:].lower() if word else "" for word in text.split())

    @staticmethod
    def _normalize_key(value: object) -> str:
        if pd.isna(value):
            return ""
        return " ".join(str(value).strip().lower().split())

    def _build_canonical_map(self, series: pd.Series) -> dict[str, str]:
        canonical: dict[str, str] = {}
        for value in series.dropna().unique():
            key = self._normalize_key(value)
            if not key:
                continue
            candidate = self.title_case_words(str(value).strip())
            existing = canonical.get(key)
            if existing is None or len(candidate) > len(existing):
                canonical[key] = candidate
        return canonical

    def _load_hierarchy_map(self, hierarchy_path: str | None) -> dict[str, str]:
        if not hierarchy_path:
            return {}

        path = resolve_project_path(hierarchy_path)
        if not path.exists() or path.stat().st_size == 0:
            return {}

        try:
            frame = pd.read_csv(path, dtype=str)
        except pd.errors.EmptyDataError:
            return {}

        if frame.empty or len(frame.columns) == 0:
            return {}

        name_column = frame.columns[-1]
        canonical: dict[str, str] = {}
        for value in frame[name_column].dropna().unique():
            key = self._normalize_key(value)
            if key:
                canonical[key] = self.title_case_words(str(value).strip())
        return canonical

    def _apply_canonical(self, value: object, canonical_map: dict[str, str]) -> object:
        if pd.isna(value):
            return pd.NA
        key = self._normalize_key(value)
        if not key:
            return pd.NA
        return canonical_map.get(key, self.title_case_words(str(value).strip()))
