"""CSV loading utilities with automatic header detection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HEADER_KEYWORDS = {
    "name",
    "code",
    "pin",
    "state",
    "district",
    "city",
    "town",
    "village",
    "road",
    "street",
    "building",
    "latitude",
    "longitude",
    "office",
    "locality",
    "block",
    "postal",
    "zip",
    "census",
    "region",
    "division",
    "circle",
    "delivery",
    "urban",
}


@dataclass
class CSVLoadResult:
    """Result of loading a CSV file."""

    dataframe: pd.DataFrame
    header_row: int
    encoding: str
    warnings: list[str]


class CSVLoader:
    """Load CSV files and detect the header row automatically."""

    def __init__(self, encodings: list[str] | None = None, max_header_scan_rows: int = 15) -> None:
        self.encodings = encodings or ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        self.max_header_scan_rows = max_header_scan_rows

    def load(self, file_path: Path) -> CSVLoadResult:
        last_error: Exception | None = None

        for encoding in self.encodings:
            try:
                preview = pd.read_csv(
                    file_path,
                    header=None,
                    nrows=self.max_header_scan_rows,
                    encoding=encoding,
                    dtype=str,
                    keep_default_na=False,
                )
                header_row = self._detect_header_row(preview)
                dataframe = pd.read_csv(
                    file_path,
                    header=header_row,
                    encoding=encoding,
                    dtype=str,
                    keep_default_na=False,
                )
                warnings: list[str] = []
                if header_row > 0:
                    warnings.append(f"Detected header at row {header_row + 1}; skipped {header_row} leading row(s).")

                dataframe.columns = [str(column).strip() for column in dataframe.columns]
                return CSVLoadResult(
                    dataframe=dataframe,
                    header_row=header_row,
                    encoding=encoding,
                    warnings=warnings,
                )
            except Exception as exc:  # noqa: BLE001 - try next encoding
                last_error = exc
                continue

        raise ValueError(f"Unable to read CSV file {file_path}: {last_error}")

    def _detect_header_row(self, preview: pd.DataFrame) -> int:
        best_row = 0
        best_score = float("-inf")

        for row_index in range(len(preview.index)):
            row = preview.iloc[row_index]
            score = self._score_header_candidate(row)
            if score > best_score:
                best_score = score
                best_row = row_index

        return best_row

    def _score_header_candidate(self, row: pd.Series) -> float:
        values = [str(value).strip() for value in row.tolist()]
        non_empty = [value for value in values if value and value.lower() != "nan"]

        if not non_empty:
            return -100.0

        if len(non_empty) == 1 and len(values) > 3:
            return -50.0

        numeric_count = sum(1 for value in non_empty if self._looks_numeric(value))
        text_count = len(non_empty) - numeric_count
        keyword_hits = sum(
            1 for value in non_empty if any(keyword in value.lower() for keyword in HEADER_KEYWORDS)
        )

        score = text_count * 2.0
        score += keyword_hits * 3.0
        score -= numeric_count * 1.5

        if len(set(non_empty)) == len(non_empty):
            score += 1.0

        return score

    @staticmethod
    def _looks_numeric(value: str) -> bool:
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return False
        return bool(re.fullmatch(r"-?\d+(\.\d+)?", cleaned))
