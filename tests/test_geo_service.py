import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import order as order_endpoint
from app.main import app
from app.services.geo_service import GeoService


def test_haversine_distance_returns_expected_distance():
    distance = GeoService.haversine_distance(10.7769, 106.7009, 10.7626, 106.6602)

    assert distance == pytest.approx(4.73, abs=0.2)


def test_validate_delivery_allows_address_inside_radius(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        order_endpoint.store_repo,
        "get_store",
        lambda store_id: {
            "id": store_id,
            "location": {"lat": 10.7769, "lng": 106.7009},
            "deliveryRadius": 5,
            "deliveryBuffer": 2,
        },
    )

    async def fake_geocode(address: str):
        return 10.776, 106.701

    async def fake_road_distance(lat1: float, lon1: float, lat2: float, lon2: float):
        return 1.2

    monkeypatch.setattr(order_endpoint.GeoService, "geocode", fake_geocode)
    monkeypatch.setattr(order_endpoint.GeoService, "get_road_distance", fake_road_distance)

    response = client.post(
        "/api/v1/orders/validate-delivery",
        json={"store_id": "store123", "customer_address": "123 Street"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ALLOWED"
    assert response.json()["distance_km"] == 1.2


def test_validate_delivery_rejects_unknown_store(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(order_endpoint.store_repo, "get_store", lambda store_id: None)

    response = client.post(
        "/api/v1/orders/validate-delivery",
        json={"store_id": "missing", "customer_address": "123 Street"},
    )

    assert response.status_code == 404
