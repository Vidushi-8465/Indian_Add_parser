"""Confidence scoring for parsed address entities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConfidenceScorer:
    """Estimate parse confidence from entity completeness."""

    base_score: float = 0.25
    entity_weight: float = 0.08
    pincode_bonus: float = 0.12
    full_address_bonus: float = 0.15

    def score(self, entities: dict[str, str | None], tokens: list[str]) -> float:
        present_fields = sum(1 for value in entities.values() if value not in (None, ""))
        confidence = self.base_score + present_fields * self.entity_weight
        if entities.get("pincode"):
            confidence += self.pincode_bonus
        if len(tokens) >= 4:
            confidence += self.full_address_bonus
        return round(min(confidence, 0.99), 4)
