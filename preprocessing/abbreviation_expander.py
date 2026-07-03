"""Expand configured abbreviations in address text fields."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from utils.file_utils import resolve_project_path


class AbbreviationExpander:
    """Replace known abbreviations with their expanded forms."""

    def __init__(self, abbreviations: dict[str, str] | None = None) -> None:
        self.abbreviations = {key.lower(): value for key, value in (abbreviations or {}).items()}

    @classmethod
    def from_file(cls, abbreviations_path: str | Path) -> AbbreviationExpander:
        path = resolve_project_path(abbreviations_path)
        if not path.exists():
            return cls({})
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls(data if isinstance(data, dict) else {})

    def expand(self, dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        if not self.abbreviations:
            return dataframe

        expanded = dataframe.copy()
        for column in columns:
            if column not in expanded.columns:
                continue
            expanded[column] = expanded[column].apply(self._expand_cell)
        return expanded

    def _expand_cell(self, value: object) -> object:
        if pd.isna(value):
            return pd.NA

        text = str(value)
        for abbreviation, replacement in sorted(self.abbreviations.items(), key=lambda item: -len(item[0])):
            pattern = re.compile(rf"\b{re.escape(abbreviation)}\b", re.IGNORECASE)
            text = pattern.sub(replacement, text)
        return text
