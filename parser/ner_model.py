"""Rule-based NER model for Indian address parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .tokenizer import QueryTokenizer


_PINCODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")


@dataclass(slots=True)
class NerModel:
    """Extract structured entities from normalized tokens."""

    tokenizer: QueryTokenizer

    BUILDING_MARKERS = {"flat", "apartment", "building", "tower", "wing", "block", "house", "plot", "shop"}
    ROAD_MARKERS = {"road", "street", "lane", "nagar", "avenue", "rd", "st"}
    LOCALITY_MARKERS = {"sector", "area", "locality", "colony", "layout", "phase", "nagar"}
    VILLAGE_MARKERS = {"village", "vill", "gram"}
    DISTRICT_MARKERS = {"district", "dist"}
    LANDMARK_MARKERS = {"near", "opposite", "behind", "beside"}
    STATE_NAMES = {
        "andhra pradesh",
        "arunachal pradesh",
        "assam",
        "bihar",
        "chhattisgarh",
        "goa",
        "gujarat",
        "haryana",
        "himachal pradesh",
        "jharkhand",
        "karnataka",
        "kerala",
        "madhya pradesh",
        "maharashtra",
        "manipur",
        "meghalaya",
        "mizoram",
        "nagaland",
        "odisha",
        "punjab",
        "rajasthan",
        "sikkim",
        "tamil nadu",
        "telangana",
        "tripura",
        "uttar pradesh",
        "uttarakhand",
        "west bengal",
        "delhi",
        "jammu and kashmir",
        "ladakh",
        "chandigarh",
        "puducherry",
        "dadra and nagar haveli",
        "daman and diu",
    }

    def detect(self, query: str | None) -> dict[str, str | None]:
        normalized = self.tokenizer.normalize(query)
        tokens = self.tokenizer.tokenize(normalized)
        return self.detect_from_tokens(tokens)

    def detect_from_tokens(self, tokens: list[str]) -> dict[str, str | None]:
        entities = {
            "building_name": None,
            "flat_number": None,
            "house_number": None,
            "road_name": None,
            "locality": None,
            "area": None,
            "village": None,
            "city": None,
            "district": None,
            "state": None,
            "pincode": None,
            "landmark": None,
        }

        remaining = list(tokens)
        entities["pincode"] = self._extract_pincode(remaining)
        entities["state"] = self._extract_state(remaining)
        entities["road_name"] = self._extract_road_name(remaining)
        entities["landmark"] = self._extract_landmark(remaining)
        entities["district"] = self._extract_marked_entity(remaining, self.DISTRICT_MARKERS)
        entities["village"] = self._extract_marked_entity(remaining, self.VILLAGE_MARKERS)

        building_name, flat_number, house_number, locality, area, city = self._extract_core_location(remaining, entities)
        entities["building_name"] = building_name
        entities["flat_number"] = flat_number
        entities["house_number"] = house_number
        entities["locality"] = locality
        entities["area"] = area
        entities["city"] = city

        return entities

    @staticmethod
    def _extract_pincode(tokens: list[str]) -> str | None:
        for token in tokens:
            if _PINCODE_PATTERN.fullmatch(token):
                return token
        return None

    @staticmethod
    def _extract_state(tokens: list[str]) -> str | None:
        for token in tokens:
            if token in QueryTokenizer.STATE_ABBREVIATIONS:
                return QueryTokenizer.STATE_ABBREVIATIONS[token].title()
        joined_two = [" ".join(tokens[index : index + 2]) for index in range(len(tokens) - 1)]
        joined_three = [" ".join(tokens[index : index + 3]) for index in range(len(tokens) - 2)]
        joined_four = [" ".join(tokens[index : index + 4]) for index in range(len(tokens) - 3)]
        for candidate in joined_two + joined_three + joined_four + tokens:
            if candidate in NerModel.STATE_NAMES:
                return candidate.title()
        return None

    def _extract_landmark(self, tokens: list[str]) -> str | None:
        marker_index = self._find_marker_index(tokens, self.LANDMARK_MARKERS)
        if marker_index is None:
            return None
        captured = tokens[marker_index : min(len(tokens), marker_index + 3)]
        return " ".join(captured).title()

    def _extract_road_name(self, tokens: list[str]) -> str | None:
        marker_index = self._find_marker_index(tokens, self.ROAD_MARKERS)
        if marker_index is None:
            return None
        start = max(0, marker_index - 2)
        captured = tokens[start : marker_index + 1]
        return " ".join(captured).title()

    @staticmethod
    def _extract_marked_entity(tokens: list[str], markers: set[str]) -> str | None:
        marker_index = None
        for index, token in enumerate(tokens):
            if token in markers:
                marker_index = index
                break
        if marker_index is None:
            return None
        captured = tokens[marker_index : min(len(tokens), marker_index + 2)]
        return " ".join(captured).title()

    def _extract_core_location(
        self,
        tokens: list[str],
        entities: dict[str, str | None],
    ) -> tuple[str | None, str | None, str | None, str | None, str | None, str | None]:
        filtered = [token for token in tokens if token != entities["pincode"]]
        state_tokens = set()
        if entities["state"]:
            state_tokens = {part.lower() for part in entities["state"].split()}
            filtered = [token for token in filtered if token not in state_tokens]
        if entities["road_name"]:
            road_tokens = {part.lower() for part in entities["road_name"].split()}
            filtered = [token for token in filtered if token not in road_tokens]
        if entities["landmark"]:
            landmark_tokens = {part.lower() for part in entities["landmark"].split()}
            filtered = [token for token in filtered if token not in landmark_tokens]
        for marker_set in (self.BUILDING_MARKERS, self.LOCALITY_MARKERS, self.VILLAGE_MARKERS, self.DISTRICT_MARKERS):
            filtered = [token for token in filtered if token not in marker_set]

        flat_number = None
        house_number = None
        building_name = None
        locality = entities["locality"]
        area = entities["area"]
        city = entities["city"]

        marker_index = self._find_marker_index(tokens, self.BUILDING_MARKERS)
        if marker_index is not None:
            if marker_index + 1 < len(tokens) and tokens[marker_index + 1].isdigit():
                flat_number = tokens[marker_index + 1]
            tail = [token for token in tokens[marker_index + 1 :] if token != entities["pincode"]]
            if flat_number and tail and tail[0] == flat_number:
                tail = tail[1:]
            tail = [token for token in tail if token not in self.BUILDING_MARKERS]
            tail = [token for token in tail if token not in self.ROAD_MARKERS]
            if len(tail) >= 3:
                building_name = " ".join(tail[:-2]).title()
                locality = locality or tail[-2].title()
                city = city or tail[-1].title()
            elif len(tail) == 2:
                building_name = tail[0].title()
                locality = locality or tail[1].title()
            elif len(tail) == 1:
                building_name = tail[0].title()

        if building_name is None:
            if len(filtered) >= 4:
                building_name = " ".join(filtered[-2:]).title()
                locality = locality or filtered[0].title()
                city = city or filtered[-3].title()
            elif len(filtered) == 3:
                building_name = " ".join(filtered[1:]).title()
                locality = locality or filtered[0].title()
                city = city or filtered[1].title()
            elif len(filtered) == 2:
                locality = locality or filtered[0].title()
                city = city or filtered[1].title()
            elif len(filtered) == 1:
                if len(tokens) == 1:
                    city = city or filtered[0].title()
                else:
                    locality = locality or filtered[0].title()

        if not area and locality:
            area = locality
        if not city and len(filtered) == 1:
            city = filtered[0].title()

        if len(tokens) == 1 and not city and not entities["state"]:
            city = tokens[0].title()
            locality = None

        if not house_number and flat_number:
            house_number = flat_number

        return building_name, flat_number, house_number, locality, area, city

    @staticmethod
    def _find_marker_index(tokens: list[str], markers: set[str]) -> int | None:
        for index, token in enumerate(tokens):
            if token in markers:
                return index
        return None
