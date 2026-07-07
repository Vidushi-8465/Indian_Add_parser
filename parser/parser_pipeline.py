"""End-to-end query processing and NER pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from interfaces.parser_interface import ParserInterface
from models.parsed_address import ParsedAddress

from .confidence import ConfidenceScorer
from .entity_mapper import EntityMapper
from .ner_model import NerModel
from .postprocessor import PostProcessor
from .tokenizer import QueryTokenizer


@dataclass(slots=True)
class ParserPipeline(ParserInterface):
    """Normalize, tokenize, detect entities, and return structured address data."""

    tokenizer: QueryTokenizer | None = None
    ner_model: NerModel | None = None
    entity_mapper: EntityMapper | None = None
    postprocessor: PostProcessor | None = None
    confidence_scorer: ConfidenceScorer | None = None

    def __post_init__(self) -> None:
        self.tokenizer = self.tokenizer or QueryTokenizer()
        self.ner_model = self.ner_model or NerModel(self.tokenizer)
        self.entity_mapper = self.entity_mapper or EntityMapper()
        self.postprocessor = self.postprocessor or PostProcessor()
        self.confidence_scorer = self.confidence_scorer or ConfidenceScorer()

    def parse(self, query: str | None) -> dict[str, Any]:
        normalized_query = self.tokenizer.normalize(query)
        tokens = self.tokenizer.tokenize(normalized_query) if normalized_query else []
        phrases = self.tokenizer.generate_phrases(tokens)
        entities = self.ner_model.detect_from_tokens(tokens)
        mapped_entities = self.entity_mapper.map_entities(entities)
        cleaned_entities = self.postprocessor.deduplicate_values(mapped_entities)
        confidence = self.confidence_scorer.score(cleaned_entities, tokens)

        parsed = ParsedAddress(
            query=query,
            normalized_query=normalized_query,
            tokens=tokens,
            phrases=phrases,
            intent=self._detect_intent(tokens, cleaned_entities),
            building_name=cleaned_entities.get("building_name"),
            flat_number=cleaned_entities.get("flat_number"),
            house_number=cleaned_entities.get("house_number"),
            road_name=cleaned_entities.get("road_name"),
            locality=cleaned_entities.get("locality"),
            area=cleaned_entities.get("area"),
            village=cleaned_entities.get("village"),
            city=cleaned_entities.get("city"),
            district=cleaned_entities.get("district"),
            state=cleaned_entities.get("state"),
            pincode=cleaned_entities.get("pincode"),
            landmark=cleaned_entities.get("landmark"),
            confidence=confidence,
        )
        return parsed.to_dict()

    @staticmethod
    def _detect_intent(tokens: list[str], entities: dict[str, str | None]) -> str:
        if not tokens:
            return "EMPTY_QUERY"
        if len(tokens) == 1 and entities.get("pincode"):
            return "PINCODE_SEARCH"
        if len(tokens) == 1 and entities.get("city"):
            return "CITY_SEARCH"
        populated_entities = sum(1 for key in ("building_name", "flat_number", "house_number", "road_name", "locality", "area", "village", "city", "district", "state", "pincode", "landmark") if entities.get(key))
        if entities.get("building_name") and (
            entities.get("pincode")
            or entities.get("locality")
            or entities.get("area")
            or entities.get("city")
            or entities.get("district")
            or entities.get("state")
            or len(tokens) >= 4
        ):
            return "FULL_ADDRESS_SEARCH"
        if populated_entities >= 3 and len(tokens) >= 4:
            return "FULL_ADDRESS_SEARCH"
        if entities.get("building_name"):
            return "BUILDING_SEARCH"
        if entities.get("road_name"):
            return "ROAD_SEARCH"
        if entities.get("locality") or entities.get("area"):
            return "LOCALITY_SEARCH"
        if entities.get("city"):
            return "CITY_SEARCH"
        if entities.get("district"):
            return "DISTRICT_SEARCH"
        if entities.get("state"):
            return "STATE_SEARCH"
        return "AUTO"
