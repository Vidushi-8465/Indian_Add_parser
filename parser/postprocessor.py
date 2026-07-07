"""Post-processing for parser and NER output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PostProcessor:
    """Clean duplicated values and enrich a partially parsed address."""

    def deduplicate_values(self, values: dict[str, str | None]) -> dict[str, str | None]:
        seen: set[str] = set()
        cleaned: dict[str, str | None] = {}
        for key, value in values.items():
            if value in (None, ""):
                cleaned[key] = value
                continue
            normalized = value.strip().lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned[key] = value
        return cleaned
