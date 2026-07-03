"""Tests for the search API."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import create_app


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)

    with patch("api.main.ping_cluster", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["elasticsearch"] is True


def test_search_endpoint_returns_candidates() -> None:
    app = create_app()
    client = TestClient(app)
    mock_result = {
        "query": "TCS Hinjewadi",
        "strategy": "fuzzy",
        "total_hits": 1,
        "took_ms": 8,
        "candidates": [
            {
                "id": "abc123",
                "score": 5.1,
                "address_hash": "abc123",
                "full_address": "TCS, Hinjewadi, Pune, Maharashtra, 411057",
                "building_name": "TCS",
                "locality": "Hinjewadi",
                "city_name": "Pune",
                "district_name": "Pune",
                "state_name": "Maharashtra",
                "pincode": "411057",
                "quality_score": 68.75,
            }
        ],
    }

    with patch("api.main.ping_cluster", return_value=True):
        with patch("api.main.get_search_service") as mock_service_factory:
            mock_service = mock_service_factory.return_value
            mock_service.search.return_value = mock_result
            response = client.post(
                "/search",
                json={"query": "TCS Hinjewadi", "strategy": "fuzzy", "size": 5},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"] == "fuzzy"
    assert payload["total_hits"] == 1
    assert payload["candidates"][0]["building_name"] == "TCS"
