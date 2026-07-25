"""Common Indian locality spelling variants used at query/rank time."""

from __future__ import annotations

from ranking.similarity import normalize_text


# Canonical key -> known spellings. Lookup is bidirectional.
_LOCALITY_ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("hinjewadi", "hinjavadi", "hinjawadi", "hinjewady"),
    ("bangalore", "bengaluru", "bengalooru"),
    ("bombay", "mumbai"),
    ("madras", "chennai"),
    ("calcutta", "kolkata"),
    ("poona", "pune"),
    ("gurgaon", "gurugram"),
    ("mysore", "mysuru"),
)


def _build_alias_map() -> dict[str, list[str]]:
    alias_map: dict[str, list[str]] = {}
    for group in _LOCALITY_ALIAS_GROUPS:
        normalized = [normalize_text(item) for item in group if item]
        for item in normalized:
            alias_map[item] = [other for other in normalized if other != item]
    return alias_map


LOCALITY_ALIASES = _build_alias_map()


def locality_variants(value: str | None) -> list[str]:
    """Return the original locality plus known spelling variants."""
    if not value:
        return []
    normalized = normalize_text(value)
    if not normalized:
        return [value]
    variants = [normalized]
    for alias in LOCALITY_ALIASES.get(normalized, []):
        if alias not in variants:
            variants.append(alias)
    return variants
