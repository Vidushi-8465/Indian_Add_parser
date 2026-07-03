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


def is_subdistrict_column(name: str) -> bool:
    """Return True when a column name refers to a sub-district/tehsil level."""
    normalized = normalize_column_name(name)
    compact = normalized.replace(" ", "")
    return (
        "subdistrict" in compact
        or normalized.startswith("tehsil")
        or normalized.startswith("taluk")
        or " tehsil" in normalized
        or " taluk" in normalized
    )


def normalize_for_deduplication(text: str) -> str:
    """
    Normalize address text for duplicate detection.

    Examples
    --------
    "TCS, Hinjewadi" -> "tcs hinjewadi"
    "TCS Hinjewadi"  -> "tcs hinjewadi"
    """
    from utils.regex_utils import DEDUP_PUNCTUATION_PATTERN

    lowered = text.strip().lower()
    lowered = DEDUP_PUNCTUATION_PATTERN.sub(" ", lowered)
    return " ".join(lowered.split())

