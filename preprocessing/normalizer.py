"""String normalization, geographic standardization, and field validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from utils.file_utils import resolve_project_path
from utils.regex_utils import PINCODE_PATTERN


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

            standardized[column] = standardized[column].apply(
                lambda value: self._apply_canonical(value, canonical_map)
            )
        return standardized

    def validate_pincode(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        if "pincode" not in dataframe.columns:
            return dataframe, 0

        validated = dataframe.copy()
        invalid_count = 0
        for index, value in validated["pincode"].items():
            if pd.isna(value):
                continue
            pincode = str(value).strip().split(".")[0]
            if not PINCODE_PATTERN.fullmatch(pincode):
                validated.at[index, "pincode"] = pd.NA
                invalid_count += 1
            else:
                validated.at[index, "pincode"] = pincode
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
        invalid_count = 0

        for index, value in validated[column].items():
            if pd.isna(value):
                continue
            try:
                number = float(str(value).strip())
            except ValueError:
                validated.at[index, column] = pd.NA
                invalid_count += 1
                self.logger.warning("Invalid {} value '{}' at row {} set to null", column, value, index)
                continue

            if number < minimum or number > maximum:
                validated.at[index, column] = pd.NA
                invalid_count += 1
                self.logger.warning(
                    "Out-of-range {} value '{}' at row {} set to null (allowed {} to {})",
                    column,
                    value,
                    index,
                    minimum,
                    maximum,
                )
            else:
                validated.at[index, column] = number

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
        if not path.exists():
            return {}

        frame = pd.read_csv(path, dtype=str)
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
