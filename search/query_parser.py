"""Query parsing and intent detection for address search."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .query_normalizer import QueryNormalizer


_PINCODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")


@dataclass(slots=True)
class QueryParseResult:
    query: str | None
    normalized_query: str
    tokens: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    intent: str = "AUTO_SEARCH"
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "tokens": list(self.tokens),
            "phrases": list(self.phrases),
            "intent": self.intent,
            "validation_errors": list(self.validation_errors),
        }


class QueryParser:
    """Parse raw queries into tokens, phrases, and a coarse search intent."""

    BUILDING_MARKERS = {"flat", "house", "houseno", "housenumber", "plot", "shop", "apartment", "tower", "wing"}
    OFFICE_MARKERS = {"office", "gpo", "headquarters", "hq", "bhavan", "bhawan", "sadan", "kendra", "karyalaya", "chamber", "chambers"}
    LANDMARK_MARKERS = {"near", "opposite", "behind", "beside", "adjacent"}
    ROAD_MARKERS = {"road", "street", "lane", "rd", "st"}
    VILLAGE_MARKERS = {"village", "vill", "gram"}
    BLOCK_MARKERS = {"block"}
    DISTRICT_MARKERS = {"district", "dist"}
    STATE_MARKERS = set(QueryNormalizer.STATE_ABBREVIATIONS.values())

    def __init__(self, normalizer: QueryNormalizer | None = None) -> None:
        self.normalizer = normalizer or QueryNormalizer()

    def parse(self, query: str | None) -> QueryParseResult:
        normalized_query = self.normalizer.normalize_query(query)
        tokens = normalized_query.split() if normalized_query else []
        phrases = self.extract_phrases(tokens)
        intent = self.detect_intent(tokens)
        validation_errors = self.validate(tokens, normalized_query)
        return QueryParseResult(
            query=query,
            normalized_query=normalized_query,
            tokens=tokens,
            phrases=phrases,
            intent=intent,
            validation_errors=validation_errors,
        )

    @staticmethod
    def extract_phrases(tokens: list[str]) -> list[str]:
        phrases: list[str] = []
        current: list[str] = []
        for token in tokens:
            if token.isdigit() or _PINCODE_PATTERN.fullmatch(token):
                if len(current) >= 2:
                    phrases.extend(QueryParser._phrases_from_segment(current))
                current = []
                continue
            current.append(token)
        if len(current) >= 2:
            phrases.extend(QueryParser._phrases_from_segment(current))
        return phrases

    @staticmethod
    def _phrases_from_segment(segment: list[str]) -> list[str]:
        phrases: list[str] = []
        limit = min(4, len(segment))
        for start in range(len(segment)):
            for end in range(start + 2, min(len(segment), start + limit) + 1):
                phrases.append(" ".join(segment[start:end]))
        return phrases

    def detect_intent(self, tokens: list[str]) -> str:
        if not tokens:
            return "AUTO_SEARCH"
        if len(tokens) == 1 and _PINCODE_PATTERN.fullmatch(tokens[0]):
            return "PINCODE_SEARCH"
        if any(token in self.BUILDING_MARKERS for token in tokens) and (len(tokens) >= 4 or any(_PINCODE_PATTERN.fullmatch(token) for token in tokens)):
            return "FULL_ADDRESS_SEARCH"
        if any(token in self.LANDMARK_MARKERS for token in tokens):
            return "NEARBY_SEARCH"
        if any(token in self.OFFICE_MARKERS for token in tokens):
            return "OFFICE_SEARCH"
        if any(token in self.BLOCK_MARKERS for token in tokens):
            return "BLOCK_SEARCH"
        if any(token in self.VILLAGE_MARKERS for token in tokens):
            return "VILLAGE_SEARCH"
        if any(token in self.DISTRICT_MARKERS for token in tokens):
            return "DISTRICT_SEARCH"
        if any(token in self.ROAD_MARKERS for token in tokens):
            return "ROAD_SEARCH"
        if any(token in self.BUILDING_MARKERS for token in tokens):
            return "BUILDING_SEARCH"
        if any(token in self.STATE_MARKERS for token in tokens):
            return "STATE_SEARCH"
        if len(tokens) == 1:
            return "CITY_SEARCH"
        if len(tokens) == 2:
            return "LOCALITY_SEARCH"
        if len(tokens) >= 4:
            return "FULL_ADDRESS_SEARCH"
        return "LOCALITY_SEARCH"

    @staticmethod
    def validate(tokens: list[str], normalized_query: str) -> list[str]:
        errors: list[str] = []
        if not normalized_query:
            errors.append("Query cannot be empty.")
            return errors
        if len(tokens) < 1:
            errors.append("Query must contain at least one token.")
        if any(token.isdigit() and len(token) not in (1, 2, 3, 4, 5, 6) for token in tokens):
            errors.append("Query contains unsupported numeric tokens.")
        if len(tokens) == 1 and tokens[0].isdigit() and not _PINCODE_PATTERN.fullmatch(tokens[0]):
            errors.append("Single numeric token is not a valid pincode.")
        if len(tokens) == 1 and _PINCODE_PATTERN.fullmatch(tokens[0]) is None and len(tokens[0]) < 2:
            errors.append("Query is too short.")
        return errors
