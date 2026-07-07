"""Parser interface for query processing and NER."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ParserInterface(ABC):
    """Contract for parsing address queries into structured entities."""

    @abstractmethod
    def parse(self, query: str | None) -> dict[str, Any]:
        raise NotImplementedError
