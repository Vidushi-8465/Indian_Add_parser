"""Structured output for parsed address queries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _compact(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


@dataclass(slots=True)
class ParsedAddress:
    query: str | None
    normalized_query: str
    tokens: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    intent: str = "AUTO"
    building_name: str | None = None
    flat_number: str | None = None
    house_number: str | None = None
    road_name: str | None = None
    locality: str | None = None
    area: str | None = None
    village: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    landmark: str | None = None
    confidence: float = 0.0
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _compact(asdict(self))
