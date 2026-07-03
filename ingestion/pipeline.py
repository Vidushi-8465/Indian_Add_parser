"""End-to-end data ingestion pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from ingestion.csv_loader import CSVLoader
from ingestion.header_detector import HeaderDetector
from ingestion.merger import DatasetMerger, SchemaStandardizer
from ingestion.validator import DatasetValidator
from utils.constants import DEFAULT_INGESTION_CONFIG, PROJECT_ROOT
from utils.file_utils import discover_data_files, ensure_parent_directory, load_yaml_config, resolve_project_path


@dataclass
class FileProcessingResult:
    """Processing summary for a single source file."""

    filename: str
    path: str
    format: str
    status: str
    rows: int = 0
    columns_before: int = 0
    columns_mapped: int = 0
    column_mapping: dict[str, str] = field(default_factory=dict)
    unmapped_columns: list[str] = field(default_factory=list)
    header_row: int | None = None
    encoding: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class IngestionPipeline:
    """Discover, validate, standardize, and merge raw CSV address datasets."""

    def __init__(self, config_path: Path | None = None) -> None:
        from app_logging.logger import setup_logging

        setup_logging()
        self.config_path = config_path or DEFAULT_INGESTION_CONFIG
        self.config = load_yaml_config(self.config_path)
        reading_config = self.config.get("reading", {})
        max_scan_rows = reading_config.get("max_header_scan_rows", 20)
        header_detector = HeaderDetector(
            column_aliases=self.config["column_aliases"],
            max_scan_rows=max_scan_rows,
        )
        self.validator = DatasetValidator()
        self.csv_loader = CSVLoader(
            header_detector=header_detector,
            encodings=reading_config.get("encodings"),
        )
        self.standardizer = SchemaStandardizer(
            standard_columns=self.config["standard_columns"],
            column_aliases=self.config["column_aliases"],
            dtype_rules=self.config.get("dtype_rules", {}),
        )
        self.merger = DatasetMerger()

    def run(self) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        start_time = perf_counter()

        source_files = self._discover_source_files()
        standardized_frames: list[pd.DataFrame] = []
        file_results: list[FileProcessingResult] = []
        validation_errors: list[str] = []
        global_warnings: list[str] = []

        if not source_files:
            global_warnings.append("No raw CSV files were discovered.")

        for source_file in source_files:
            result, standardized_frame = self._process_file(source_file)
            file_results.append(result)

            if result.errors:
                validation_errors.extend(result.errors)
                continue

            if standardized_frame is not None:
                standardized_frames.append(standardized_frame)

        master_columns = self.config["standard_columns"]
        master_dataset = self.merger.merge(standardized_frames, master_columns)

        output_dataset_path = resolve_project_path(self.config["paths"]["master_dataset"])
        output_metadata_path = resolve_project_path(self.config["paths"]["master_metadata"])
        ensure_parent_directory(output_dataset_path)
        ensure_parent_directory(output_metadata_path)

        master_dataset.to_csv(output_dataset_path, index=False)
        completed_at = datetime.now(timezone.utc)

        metadata = {
            "pipeline": "ingestion",
            "version": "1.0",
            "input_format": "csv",
            "config_path": self._relative_path(self.config_path),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "processing_time_seconds": round(perf_counter() - start_time, 3),
            "files_discovered": len(source_files),
            "files_processed": sum(1 for result in file_results if result.status == "success"),
            "files_failed": sum(1 for result in file_results if result.status == "failed"),
            "total_rows": int(len(master_dataset.index)),
            "total_columns": int(len(master_dataset.columns)),
            "standard_columns": master_columns,
            "output_dataset": self._relative_path(output_dataset_path),
            "output_metadata": self._relative_path(output_metadata_path),
            "merge_statistics": self.merger.get_statistics(),
            "files": [asdict(result) for result in file_results],
            "validation_errors": validation_errors,
            "warnings": global_warnings + [warning for result in file_results for warning in result.warnings],
        }

        with output_metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

        return metadata

    def _discover_source_files(self) -> list[Path]:
        paths = self.config["paths"]
        discovery = self.config.get("discovery", {})
        raw_dir = paths.get("raw_data_dir") or paths.get("raw_csv_dir", "datasets/raw/csv")
        directories = [resolve_project_path(raw_dir)]
        extensions = discovery.get("csv_extensions", [".csv"])
        return discover_data_files(directories, extensions, recursive=discovery.get("recursive", True))

    def _process_file(self, source_file: Path) -> tuple[FileProcessingResult, pd.DataFrame | None]:
        result = FileProcessingResult(
            filename=source_file.name,
            path=self._relative_path(source_file),
            format=source_file.suffix.lower().lstrip("."),
            status="failed",
        )

        try:
            if source_file.suffix.lower() != ".csv":
                result.errors.append(
                    f"{source_file.name}: only CSV files are supported. Convert Excel files to CSV before ingestion."
                )
                return result, None

            loaded = self.csv_loader.load(source_file)
            result.warnings.extend(loaded.warnings)
            result.header_row = loaded.header_row
            result.encoding = loaded.encoding
            result.columns_before = len(loaded.dataframe.columns)

            dataframe = self.validator.drop_empty_rows(loaded.dataframe)
            validation = self.validator.validate(dataframe, source_file.name)
            result.warnings.extend(validation.warnings)

            if not validation.is_valid:
                result.errors.extend(validation.errors)
                return result, None

            standardization = self.standardizer.standardize(dataframe, source_file.name)
            result.column_mapping = standardization.column_mapping
            result.unmapped_columns = standardization.unmapped_columns
            result.columns_mapped = len(standardization.column_mapping)
            result.rows = len(standardization.dataframe.index)
            result.status = "success"

            if standardization.unmapped_columns:
                result.warnings.append(
                    f"Unmapped columns kept out of master schema: {standardization.unmapped_columns}"
                )
            return result, standardization.dataframe
        except Exception as exc:  # noqa: BLE001 - capture per-file failures
            result.errors.append(str(exc))
            return result, None

    @staticmethod
    def _relative_path(path: Path) -> str:
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)
