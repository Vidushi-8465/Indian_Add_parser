"""Map cleaned CSV rows to Elasticsearch documents."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

_NULL_LIKE = {"", "nan", "none", "null", "na", "n/a", "<na>"}


def _clean_value(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in _NULL_LIKE:
        return None
    return text


def _parse_coordinate(value: object) -> float | None:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number


class DocumentMapper:
    """Convert preprocessed dataframe rows into Elasticsearch documents."""

    def __init__(self, id_field: str = "address_hash", fallback_id_prefix: str = "row") -> None:
        self.id_field = id_field
        self.fallback_id_prefix = fallback_id_prefix

    def map_row(self, row: pd.Series, row_number: int) -> tuple[str, dict[str, Any]] | None:
        document: dict[str, Any] = {}
        for column, value in row.items():
            cleaned = _clean_value(value)
            if cleaned is not None:
                document[str(column)] = cleaned

        if not document.get("full_address") and not document.get("locality") and not document.get("pincode"):
            return None

        latitude = _parse_coordinate(row.get("latitude"))
        longitude = _parse_coordinate(row.get("longitude"))
        if latitude is not None and longitude is not None and -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
            document["location"] = {"lat": latitude, "lon": longitude}

        quality = _clean_value(row.get("quality_score"))
        if quality is not None:
            try:
                document["quality_score"] = float(quality)
            except ValueError:
                pass

        document["indexed_at"] = datetime.now(timezone.utc).isoformat()
        document_id = self._resolve_document_id(row, row_number, document)
        return document_id, document

    def map_dataframe(self, frame: pd.DataFrame, start_row: int = 0) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for offset, (_, row) in enumerate(frame.iterrows()):
            mapped = self.map_row(row, start_row + offset)
            if mapped is None:
                continue
            document_id, document = mapped
            actions.append({"_id": document_id, "_source": document})
        return actions

    def _resolve_document_id(self, row: pd.Series, row_number: int, document: dict[str, Any]) -> str:
        preferred = _clean_value(row.get(self.id_field))
        if preferred:
            return preferred

        pincode = _clean_value(row.get("pincode")) or "na"
        locality = (_clean_value(row.get("locality")) or "na").replace(" ", "_")[:40]
        return f"{self.fallback_id_prefix}-{row_number}-{pincode}-{locality}"
