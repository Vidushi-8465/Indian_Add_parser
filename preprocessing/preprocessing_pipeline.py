"""End-to-end preprocessing pipeline for the master dataset."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd
from loguru import logger

from preprocessing.abbreviation_expander import AbbreviationExpander
from preprocessing.address_builder import AddressBuilder
from preprocessing.address_deduplicator import AddressDeduplicator
from preprocessing.cleaner import DataCleaner
from preprocessing.deduplicator import Deduplicator
from preprocessing.normalizer import AddressNormalizer
from preprocessing.null_handler import NullHandler
from preprocessing.quality_scorer import QualityScorer
from preprocessing.report_generator import ReportGenerator
from preprocessing.statistics import DatasetStatistics
from preprocessing.symbol_normalizer import SymbolNormalizer
from preprocessing.unicode_normalizer import UnicodeNormalizer
from utils.constants import DEFAULT_PREPROCESSING_CONFIG, PROJECT_ROOT
from utils.file_utils import ensure_parent_directory, load_yaml_config, resolve_project_path


@dataclass
class PreprocessingStats:
    rows_input: int = 0
    rows_output: int = 0
    duplicate_rows_removed: int = 0
    duplicate_addresses_removed: int = 0
    empty_rows_removed: int = 0
    empty_columns_removed: int = 0
    invalid_pincodes: int = 0
    invalid_latitude_values: int = 0
    invalid_longitude_values: int = 0
    filled_values: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class PreprocessingPipeline:
    """Clean, normalize, validate, and export the ingested master dataset."""

    def __init__(self, config_path: Path | None = None) -> None:
        from app_logging.logger import setup_logging

        setup_logging()
        self.logger = logger.bind(module="preprocessing.pipeline")
        self.config_path = config_path or DEFAULT_PREPROCESSING_CONFIG
        self.config = load_yaml_config(self.config_path)
        self.deduplicator = Deduplicator()
        self.address_deduplicator = AddressDeduplicator()
        self.cleaner = DataCleaner()
        self.symbol_normalizer = SymbolNormalizer()
        self.unicode_normalizer = UnicodeNormalizer()
        self.null_handler = NullHandler(self.config.get("null_like_values"))
        self.abbreviation_expander = AbbreviationExpander.from_file(
            self.config["paths"]["abbreviations"]
        )
        self.normalizer = AddressNormalizer()
        self.address_builder = AddressBuilder()
        self.quality_scorer = QualityScorer(self.config.get("quality_weights"))
        self.statistics = DatasetStatistics()
        self.report_generator = ReportGenerator()

    def run(self) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        pipeline_start = perf_counter()
        stats = PreprocessingStats()

        input_path = resolve_project_path(self.config["paths"]["input_dataset"])
        output_path = resolve_project_path(self.config["paths"]["output_dataset"])
        metadata_path = resolve_project_path(self.config["paths"]["output_metadata"])
        report_path = resolve_project_path(self.config["paths"]["preprocessing_report"])

        self.logger.info("Starting preprocessing | input={}", input_path)

        step_start = perf_counter()
        dataframe = pd.read_csv(input_path, dtype=str, keep_default_na=False)
        stats.rows_input = len(dataframe.index)
        self._log_step("Loaded input dataset", step_start, stats.rows_input)

        string_columns = self._resolve_string_columns(dataframe)
        name_columns = [column for column in self.config.get("name_columns", []) if column in dataframe.columns]
        geographic_columns = [
            column
            for column in ["state_name", "district_name", "city_name", "subdistrict_name", "locality"]
            if column in dataframe.columns
        ]
        symbol_columns = [
            column for column in self.config.get("symbol_normalization_columns", []) if column in dataframe.columns
        ]

        step_start = perf_counter()
        dataframe, stats.duplicate_rows_removed = self.deduplicator.remove_duplicates(
            dataframe,
            subset_columns=self.config.get("deduplication", {}).get("subset_columns"),
            keep=self.config.get("deduplication", {}).get("keep", "first"),
        )
        self._log_step(
            f"Removed duplicate rows ({stats.duplicate_rows_removed})",
            step_start,
            len(dataframe.index),
        )

        step_start = perf_counter()
        dataframe, stats.empty_rows_removed = self.cleaner.remove_empty_rows(dataframe)
        dataframe, stats.empty_columns_removed = self.cleaner.remove_empty_columns(dataframe)
        string_columns = self._resolve_string_columns(dataframe)
        self._log_step(
            f"Removed empty rows/columns ({stats.empty_rows_removed}/{stats.empty_columns_removed})",
            step_start,
            len(dataframe.index),
        )

        step_start = perf_counter()
        dataframe = self.cleaner.clean_invalid_characters(dataframe, string_columns)
        dataframe = self.unicode_normalizer.normalize(dataframe, string_columns)
        dataframe = self.null_handler.normalize_nulls(dataframe, string_columns)
        self._log_step("Cleaned text and normalized nulls", step_start, len(dataframe.index))

        step_start = perf_counter()
        dataframe, stats.filled_values = self.null_handler.fill_missing_values(
            dataframe,
            self.config.get("fill_hierarchy", {}),
        )
        self._log_step("Filled missing hierarchy values", step_start, len(dataframe.index))

        step_start = perf_counter()
        abbreviation_columns = [
            column for column in self.config.get("abbreviation_columns", []) if column in dataframe.columns
        ]
        dataframe = self.abbreviation_expander.expand(dataframe, abbreviation_columns)
        dataframe = self.symbol_normalizer.normalize(dataframe, symbol_columns)
        self._log_step("Expanded abbreviations and normalized symbols", step_start, len(dataframe.index))

        step_start = perf_counter()
        dataframe = self.normalizer.normalize_strings(dataframe, name_columns)
        dataframe = self.normalizer.standardize_geographic_names(
            dataframe,
            geographic_columns,
            hierarchy_paths={
                "state_name": self.config["paths"].get("hierarchy_states"),
                "district_name": self.config["paths"].get("hierarchy_districts"),
                "city_name": self.config["paths"].get("hierarchy_cities"),
            },
        )
        self._log_step("Standardized geographic names", step_start, len(dataframe.index))

        step_start = perf_counter()
        dataframe, stats.invalid_pincodes = self.normalizer.validate_pincode(dataframe)
        dataframe, invalid_coordinates = self.normalizer.validate_coordinates(dataframe)
        stats.invalid_latitude_values = invalid_coordinates["latitude"]
        stats.invalid_longitude_values = invalid_coordinates["longitude"]
        self._log_step(
            f"Validated pincodes/coordinates (invalid pincodes={stats.invalid_pincodes})",
            step_start,
            len(dataframe.index),
        )

        step_start = perf_counter()
        dataframe = self.address_builder.build(
            dataframe,
            components=self.config.get("full_address_components"),
            separator=self.config.get("full_address_separator", ", "),
        )
        self._log_step("Built full_address", step_start, len(dataframe.index))

        step_start = perf_counter()
        dataframe = self.address_deduplicator.add_address_hash(dataframe)
        dataframe, stats.duplicate_addresses_removed = self.address_deduplicator.remove_address_duplicates(
            dataframe
        )
        self._log_step(
            f"Deduplicated addresses ({stats.duplicate_addresses_removed} removed)",
            step_start,
            len(dataframe.index),
        )

        step_start = perf_counter()
        dataframe = self.quality_scorer.score(dataframe)
        self._log_step("Computed quality scores", step_start, len(dataframe.index))

        step_start = perf_counter()
        dataset_statistics = self.statistics.compute(dataframe)
        stats.rows_output = len(dataframe.index)
        self._log_step("Computed dataset statistics", step_start, len(dataframe.index))

        step_start = perf_counter()
        ensure_parent_directory(output_path)
        ensure_parent_directory(metadata_path)
        dataframe.to_csv(output_path, index=False)
        self._log_step(f"Wrote output dataset to {output_path.name}", step_start, stats.rows_output)

        completed_at = datetime.now(timezone.utc)
        metadata = {
            "pipeline": "preprocessing",
            "version": "1.1",
            "config_path": self._relative_path(self.config_path),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "processing_time_seconds": round(perf_counter() - pipeline_start, 3),
            "input_dataset": self._relative_path(input_path),
            "output_dataset": self._relative_path(output_path),
            "preprocessing_report": self._relative_path(report_path),
            "statistics": asdict(stats),
            "dataset_statistics": dataset_statistics,
        }

        with metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

        self.report_generator.generate(report_path, metadata, dataset_statistics)
        self.logger.info(
            "Preprocessing completed | rows_in={} | rows_out={} | total_time={:.1f}s | output={}",
            stats.rows_input,
            stats.rows_output,
            metadata["processing_time_seconds"],
            output_path,
        )
        return metadata

    def _log_step(self, message: str, step_start: float, rows: int) -> None:
        elapsed = perf_counter() - step_start
        self.logger.info("{} | rows={} | {:.1f}s", message, rows, elapsed)

    def _resolve_string_columns(self, dataframe: pd.DataFrame) -> list[str]:
        configured = self.config.get("string_columns", [])
        resolved = [column for column in configured if column in dataframe.columns]
        for column in dataframe.select_dtypes(include=["object", "string"]).columns:
            if column not in resolved:
                resolved.append(column)
        return resolved

    @staticmethod
    def _relative_path(path: Path) -> str:
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)
