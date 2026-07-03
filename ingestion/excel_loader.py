"""Excel loading utilities with automatic header detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ingestion.csv_loader import CSVLoader


@dataclass
class ExcelLoadResult:
    """Result of loading an Excel file."""

    dataframe: pd.DataFrame
    header_row: int
    sheet_name: str
    warnings: list[str]


class ExcelLoader:
    """Load Excel files and detect the header row automatically."""

    def __init__(self, max_header_scan_rows: int = 15) -> None:
        self.max_header_scan_rows = max_header_scan_rows
        self._header_detector = CSVLoader(max_header_scan_rows=max_header_scan_rows)

    def load(self, file_path: Path, sheet_name: str | int | None = 0) -> ExcelLoadResult:
        preview = pd.read_excel(
            file_path,
            header=None,
            nrows=self.max_header_scan_rows,
            sheet_name=sheet_name,
            dtype=str,
        )
        if isinstance(preview, dict):
            first_sheet = next(iter(preview))
            preview = preview[first_sheet]
            sheet_name = first_sheet

        header_row = self._header_detector._detect_header_row(preview)
        dataframe = pd.read_excel(
            file_path,
            header=header_row,
            sheet_name=sheet_name,
            dtype=str,
        )
        if isinstance(dataframe, dict):
            first_sheet = next(iter(dataframe))
            dataframe = dataframe[first_sheet]
            sheet_name = first_sheet

        warnings: list[str] = []
        if header_row > 0:
            warnings.append(f"Detected header at row {header_row + 1}; skipped {header_row} leading row(s).")

        dataframe.columns = [str(column).strip() for column in dataframe.columns]
        return ExcelLoadResult(
            dataframe=dataframe,
            header_row=header_row,
            sheet_name=str(sheet_name),
            warnings=warnings,
        )
