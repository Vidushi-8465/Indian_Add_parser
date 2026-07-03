"""CSV loading utilities with automatic header detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from loguru import logger

from ingestion.header_detector import HeaderDetector


@dataclass
class CSVLoadResult:
    """Result of loading a CSV file."""

    dataframe: pd.DataFrame
    header_row: int
    encoding: str
    warnings: list[str]


class CSVLoader:
    """Load CSV files and detect the header row automatically."""

    def __init__(
        self,
        header_detector: HeaderDetector,
        encodings: list[str] | None = None,
    ) -> None:
        self.header_detector = header_detector
        self.encodings = encodings or ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        self.logger = logger.bind(module="csv_loader")

    def load(self, file_path: Path) -> CSVLoadResult:
        path = Path(file_path)
        last_error: Exception | None = None

        for encoding in self.encodings:
            try:
                preview = pd.read_csv(
                    path,
                    header=None,
                    nrows=self.header_detector.max_scan_rows,
                    encoding=encoding,
                    dtype=str,
                    keep_default_na=False,
                )
                detection = self.header_detector.detect(preview, source_file=path)
                dataframe = pd.read_csv(
                    path,
                    header=detection.header_row,
                    encoding=encoding,
                    dtype=str,
                    keep_default_na=False,
                )
                warnings: list[str] = []
                if detection.header_row > 0:
                    warnings.append(
                        f"Detected header at row {detection.header_row + 1}; "
                        f"skipped {detection.header_row} leading row(s)."
                    )

                dataframe.columns = [str(column).strip() for column in dataframe.columns]
                rows_loaded = len(dataframe.index)
                self.logger.info(
                    "Loaded {} rows from CSV '{}' using encoding '{}'",
                    rows_loaded,
                    path.name,
                    encoding,
                )
                return CSVLoadResult(
                    dataframe=dataframe,
                    header_row=detection.header_row,
                    encoding=encoding,
                    warnings=warnings,
                )
            except Exception as exc:  # noqa: BLE001 - try next encoding
                last_error = exc
                continue

        raise ValueError(f"Unable to read CSV file {path}: {last_error}")
