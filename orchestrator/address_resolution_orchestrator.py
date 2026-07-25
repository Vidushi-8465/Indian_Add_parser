"""Top-level address resolution orchestrator (Phase 5: Final Ranking).

Thin high-level entry point over ``SearchService`` that returns the single best
address for a query — plus its confidence, a match explanation, and a few
alternatives. This is the "give me the top-1 at the end" contract.
"""

from __future__ import annotations

from typing import Any

from search.search_service import SearchService


class AddressResolutionOrchestrator:
    """Resolve a free-text query to the single best matching address."""

    def __init__(self, client: Any, config: dict[str, Any]) -> None:
        self.service = SearchService(client=client, config=config)

    def resolve(
        self,
        query: str | None = None,
        *,
        max_alternatives: int = 5,
        **search_kwargs: Any,
    ) -> dict[str, Any]:
        """Run the full pipeline and return the best address + alternatives.

        Returns a compact payload:
            {
              "query", "intent", "strategy", "total_hits",
              "best_match": {full_address, confidence, explanation, ...} | None,
              "alternatives": [ ...next best candidates... ],
            }
        """
        result = self.service.search(query=query, **search_kwargs)
        results = result.get("results", [])
        best = result.get("best_match")
        best_address = (best or {}).get("full_address")
        alternatives = [
            item
            for item in results
            if item.get("full_address") != best_address
        ][:max_alternatives]
        return {
            "query": result.get("query"),
            "intent": result.get("intent"),
            "strategy": result.get("strategy"),
            "total_hits": result.get("total_hits", 0),
            "best_match": best,
            "alternatives": alternatives,
        }
