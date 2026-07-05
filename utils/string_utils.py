"""String normalization helpers used during ingestion."""

from __future__ import annotations

import re

import pandas as pd

_NULL_LIKE = {"", "nan", "none", "null", "na", "n/a", "-", "--", "."}


def coerce_identifier_string(value: object) -> object:
    """Convert administrative codes and pincodes to clean string values."""
    if value is None:
        return pd.NA
    if isinstance(value, float) and pd.isna(value):
        return pd.NA

    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        text = str(value).strip()
        return text if text else pd.NA

    text = str(value).strip()
    if not text or text.lower() in _NULL_LIKE:
        return pd.NA

    text = " ".join(text.split())
    if text.endswith(".0"):
        integer_part = text[:-2]
        if integer_part.isdigit():
            return integer_part
    return text


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
        or normalized.startswith("sub district")
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

