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


def is_subdistrict_column(normalized_name: str) -> bool:
    """Return True when a normalized column name refers to a sub-district/tehsil level."""
    compact = normalized_name.replace(" ", "")
    return (
        "subdistrict" in compact
        or "subdistrict" in normalized_name
        or normalized_name.startswith("tehsil ")
        or normalized_name.startswith("taluk ")
        or " tehsil" in normalized_name
        or " taluk" in normalized_name
    )
