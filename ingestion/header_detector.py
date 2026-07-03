"""Header row detection using column aliases from ingestion config."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from loguru import logger

from utils.string_utils import normalize_column_name


@dataclass
class HeaderDetectionResult:
    """Outcome of scanning preview rows for a header."""

    header_row: int
    score: float
    matched_aliases: list[str] = field(default_factory=list)
    row_preview: list[str] = field(default_factory=list)


class HeaderDetector:
    """Detect the header row by scoring alias matches across preview rows."""

    def __init__(
        self,
        column_aliases: dict[str, list[str]],
        max_scan_rows: int = 20,
    ) -> None:
        self.max_scan_rows = max_scan_rows
        self.known_aliases = self._build_known_aliases(column_aliases)
        self.logger = logger.bind(module="header_detector")

    def detect(
        self,
        preview: pd.DataFrame,
        source_file: str | Path | None = None,
    ) -> HeaderDetectionResult:
        """Return the 0-based row index with the highest alias match score."""
        best_row = 0
        best_score = float("-inf")
        best_matches: list[str] = []
        best_preview: list[str] = []

        scan_limit = min(len(preview.index), self.max_scan_rows)
        for row_index in range(scan_limit):
            row = preview.iloc[row_index]
            score, matches, row_values = self._score_row(row)
            if score > best_score:
                best_score = score
                best_row = row_index
                best_matches = matches
                best_preview = row_values

        result = HeaderDetectionResult(
            header_row=best_row,
            score=best_score,
            matched_aliases=best_matches,
            row_preview=best_preview,
        )

        file_label = Path(source_file).name if source_file else "preview"
        self.logger.info(
            "Detected header row {} (1-based: {}) for '{}' | score={} | matched_aliases={}",
            result.header_row,
            result.header_row + 1,
            file_label,
            result.score,
            result.matched_aliases,
        )
        return result

    def _score_row(self, row: pd.Series) -> tuple[float, list[str], list[str]]:
        values = [str(value).strip() for value in row.tolist()]
        non_empty = [value for value in values if value and value.lower() != "nan"]

        if not non_empty:
            return -100.0, [], values

        if len(non_empty) == 1 and len(values) > 3:
            return -50.0, [], values

        matched_aliases: list[str] = []
        for value in non_empty:
            normalized = normalize_column_name(value)
            if normalized in self.known_aliases and normalized not in matched_aliases:
                matched_aliases.append(normalized)

        alias_score = float(len(matched_aliases))

        numeric_count = sum(1 for value in non_empty if self._looks_numeric(value))
        alias_score -= numeric_count * 0.5

        if matched_aliases and len(set(non_empty)) == len(non_empty):
            alias_score += 0.5

        return alias_score, matched_aliases, values

    def _build_known_aliases(self, column_aliases: dict[str, list[str]]) -> set[str]:
        known: set[str] = set()
        for standard_name, aliases in column_aliases.items():
            known.add(normalize_column_name(standard_name))
            for alias in aliases:
                known.add(normalize_column_name(alias))
        return known

    @staticmethod
    def _looks_numeric(value: str) -> bool:
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return False
        return bool(re.fullmatch(r"-?\d+(\.\d+)?", cleaned))
