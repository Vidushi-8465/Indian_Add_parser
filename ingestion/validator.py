"""Dataset validation for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationResult:
    """Outcome of validating a single dataset."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0


class DatasetValidator:
    """Validate raw datasets before schema standardization."""

    def validate(self, dataframe: pd.DataFrame, source_name: str) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if dataframe is None:
            errors.append(f"{source_name}: dataset could not be loaded.")
            return ValidationResult(is_valid=False, errors=errors)

        if dataframe.empty:
            errors.append(f"{source_name}: dataset is empty.")
            return ValidationResult(is_valid=False, errors=errors)

        if len(dataframe.columns) == 0:
            errors.append(f"{source_name}: dataset has no columns.")
            return ValidationResult(is_valid=False, errors=errors)

        unnamed_columns = [column for column in dataframe.columns if str(column).startswith("Unnamed")]
        if len(unnamed_columns) == len(dataframe.columns):
            errors.append(f"{source_name}: no usable column headers were detected.")
            return ValidationResult(is_valid=False, errors=errors)

        if unnamed_columns:
            warnings.append(
                f"{source_name}: ignored {len(unnamed_columns)} unnamed column(s)."
            )

        duplicate_columns = dataframe.columns[dataframe.columns.duplicated()].tolist()
        if duplicate_columns:
            errors.append(
                f"{source_name}: duplicate column names found: {duplicate_columns}"
            )

        all_null_rows = int(dataframe.isna().all(axis=1).sum())
        if all_null_rows:
            warnings.append(f"{source_name}: removed {all_null_rows} completely empty row(s).")

        if len(dataframe.index) == 0:
            errors.append(f"{source_name}: dataset contains no data rows after cleanup.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            row_count=len(dataframe.index),
            column_count=len(dataframe.columns),
        )

    def drop_empty_rows(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where every value is null or blank."""
        cleaned = dataframe.copy()
        cleaned = cleaned.dropna(how="all")
        blank_mask = cleaned.apply(
            lambda row: row.astype(str).str.strip().eq("").all(),
            axis=1,
        )
        return cleaned.loc[~blank_mask].reset_index(drop=True)
