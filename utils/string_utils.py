"""String normalization helpers used during ingestion."""

from __future__ import annotations

import re


def normalize_column_name(name: object) -> str:
    """Normalize a column name for alias matching."""
    if name is None:
        return ""

    text = str(name).strip().lower()
    text = text.replace("*", "")
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[._\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
