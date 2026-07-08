"""Rule-based entity detection for search queries."""

from __future__ import annotations

import re
from typing import Iterable

from .query_normalizer import QueryNormalizer
from .search_results import SearchEntities


_PINCODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")


class EntityDetector:
    """Extract likely address entities from normalized query tokens."""

    BUILDING_MARKERS = {"flat", "house", "building", "plot", "shop", "apartment", "tower", "wing"}
    ROAD_MARKERS = {"road", "street", "lane", "rd", "st", "avenue", "ave", "road no", "street no"}
    LOCALITY_MARKERS = {"sector", "layout", "colony", "nagar", "phase", "block", "society", "area", "enclave", "complex", "vihar"}
    VILLAGE_MARKERS = {"village", "vill", "gram"}
    BLOCK_MARKERS = {"block"}
    TALUKA_MARKERS = {"taluka", "tehsil", "tal"}
    DISTRICT_MARKERS = {"district", "dist"}

    def __init__(self, normalizer: QueryNormalizer | None = None) -> None:
        self.normalizer = normalizer or QueryNormalizer()

    def detect(self, query: str | None, tokens: list[str]) -> SearchEntities:
        normalized_tokens = self.normalizer.normalize_tokens(tokens)
        entity = SearchEntities()

        entity.pincode = self._detect_pincode(normalized_tokens)
        entity.state = self._detect_state(normalized_tokens)
        entity.road_name = self._detect_road_name(normalized_tokens)
        entity.district = self._detect_labeled_entity(normalized_tokens, self.DISTRICT_MARKERS)
        entity.village = self._detect_labeled_entity(normalized_tokens, self.VILLAGE_MARKERS)
        entity.block = self._detect_labeled_entity(normalized_tokens, self.BLOCK_MARKERS)
        entity.taluka = self._detect_labeled_entity(normalized_tokens, self.TALUKA_MARKERS)

        building_name, flat_number, locality, city = self._split_remaining_tokens(normalized_tokens, entity)
        entity.building_name = building_name
        entity.flat_number = flat_number
        entity.locality = locality
        entity.city = city

        if not entity.city and entity.state and len(normalized_tokens) == 1:
            entity.city = normalized_tokens[0]

        return entity

    @staticmethod
    def _detect_pincode(tokens: list[str]) -> str | None:
        for token in tokens:
            if _PINCODE_PATTERN.fullmatch(token):
                return token
        return None

    def _detect_state(self, tokens: list[str]) -> str | None:
        states = set(QueryNormalizer.STATE_ABBREVIATIONS.values())
        joined_tokens = [" ".join(tokens[index : index + 2]) for index in range(len(tokens) - 1)]
        joined_tokens.extend(" ".join(tokens[index : index + 3]) for index in range(len(tokens) - 2))
        for candidate in joined_tokens + tokens:
            if candidate in states:
                return candidate.title()
        for token in tokens:
            if token in QueryNormalizer.STATE_ABBREVIATIONS:
                return QueryNormalizer.STATE_ABBREVIATIONS[token].title()
        return None

    @staticmethod
    def _detect_labeled_entity(tokens: list[str], markers: set[str]) -> str | None:
        for index, token in enumerate(tokens):
            if token not in markers:
                continue
            captured = [token]
            if index > 0 and tokens[index - 1].isdigit():
                captured.insert(0, tokens[index - 1])
            if index + 1 < len(tokens) and tokens[index + 1].isalpha():
                captured.append(tokens[index + 1])
            return " ".join(captured).title()
        return None

    def _detect_road_name(self, tokens: list[str]) -> str | None:
        for index, token in enumerate(tokens):
            if token not in self.ROAD_MARKERS:
                continue
            start = max(0, index - 3)
            captured = tokens[start : index + 1]
            if len(captured) == 1 and index > 0:
                captured.insert(0, tokens[index - 1])
            return " ".join(captured).title()
        return None

    def _detect_flat_number(self, tokens: list[str]) -> str | None:
        for index, token in enumerate(tokens):
            if token == "flat" and index + 1 < len(tokens) and tokens[index + 1].isdigit():
                return tokens[index + 1]
            if token == "house":
                if index + 2 < len(tokens) and tokens[index + 1] == "number" and tokens[index + 2].isdigit():
                    return tokens[index + 2]
                if index + 1 < len(tokens) and tokens[index + 1].isdigit():
                    return tokens[index + 1]
        return None

    def _split_remaining_tokens(self, tokens: list[str], entity: SearchEntities) -> tuple[str | None, str | None, str | None, str | None]:
        remaining = [token for token in tokens if token != entity.pincode]
        if entity.state:
            state_tokens = {part.lower() for part in entity.state.split()}
            remaining = [token for token in remaining if token not in state_tokens]

        filtered = [token for token in remaining if token not in self.BUILDING_MARKERS]
        filtered = [token for token in filtered if token not in self.ROAD_MARKERS]
        filtered = [token for token in filtered if token not in self.LOCALITY_MARKERS]
        filtered = [token for token in filtered if token not in self.VILLAGE_MARKERS]
        filtered = [token for token in filtered if token not in self.BLOCK_MARKERS]
        filtered = [token for token in filtered if token not in self.TALUKA_MARKERS]
        filtered = [token for token in filtered if token not in self.DISTRICT_MARKERS]

        if entity.road_name:
            road_tokens = {part.lower() for part in entity.road_name.split()}
            filtered = [token for token in filtered if token not in road_tokens]

        building_name = None
        flat_number = self._detect_flat_number(tokens)
        locality = entity.locality
        city = entity.city

        marker_index = self._find_marker_index(tokens, self.BUILDING_MARKERS)
        if marker_index is not None:
            tail = [token for token in tokens[marker_index + 1 :] if token != entity.pincode]
            if flat_number:
                tail = [token for token in tail if token != flat_number]
            tail = [token for token in tail if token not in self.BUILDING_MARKERS]
            tail = [token for token in tail if token not in self.ROAD_MARKERS]
            tail = [token for token in tail if token not in self.LOCALITY_MARKERS]
            if len(tail) >= 3:
                building_name = " ".join(tail[:-2]).title() or None
                locality = locality or tail[-2].title()
                city = city or tail[-1].title()
            elif len(tail) == 2:
                building_name = tail[0].title()
                locality = locality or tail[1].title()
            elif len(tail) == 1:
                building_name = tail[0].title()

        if building_name is None and len(filtered) >= 4:
            building_name = " ".join(filtered[:2]).title()
            locality = locality or filtered[-2].title()
            city = city or filtered[-1].title()
        elif building_name is None and len(filtered) == 3:
            building_name = filtered[0].title()
            locality = locality or filtered[1].title()
            city = city or filtered[2].title()
        elif building_name is None and len(filtered) == 2:
            locality = locality or filtered[0].title()
            city = city or filtered[1].title()
        elif building_name is None and len(filtered) == 1:
            city = city or filtered[0].title()

        if locality is None and len(filtered) >= 2:
            locality = filtered[-2].title()
        if city is None and filtered:
            city = filtered[-1].title()

        return building_name, flat_number, locality, city

    @staticmethod
    def _find_marker_index(tokens: list[str], markers: Iterable[str]) -> int | None:
        marker_set = set(markers)
        for index, token in enumerate(tokens):
            if token in marker_set:
                return index
        return None
