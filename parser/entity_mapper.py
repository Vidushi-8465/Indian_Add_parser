"""Map NER output to a normalized parsed-address structure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EntityMapper:
    """Normalize model output keys and title-case the human-readable values."""

    def map_entities(self, entities: dict[str, str | None]) -> dict[str, str | None]:
        mapped = {
            "building_name": entities.get("building_name"),
            "flat_number": entities.get("flat_number"),
            "house_number": entities.get("house_number"),
            "road_name": entities.get("road_name"),
            "locality": entities.get("locality"),
            "area": entities.get("area"),
            "village": entities.get("village"),
            "city": entities.get("city"),
            "district": entities.get("district"),
            "state": entities.get("state"),
            "pincode": entities.get("pincode"),
            "landmark": entities.get("landmark"),
        }
        return {key: value for key, value in mapped.items() if value not in (None, "")}
