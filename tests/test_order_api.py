from datetime import datetime

from fastapi.testclient import TestClient

from app.api.v1.endpoints import order as order_endpoint
from app.main import app
from app.schemas.order import OrderResponse


client = TestClient(app)


def test_create_order_endpoint_returns_cod_order(monkeypatch):
    def fake_create_order(request):
        assert request.payment_method == "COD"
        return OrderResponse(
            order_id="COD_123",
            store_id=request.store_id,
            customer_name=request.customer_name,
            phone_number=request.phone_number,
            address=request.address,
            order_info=request.order_info,
            items=request.items,
            total_amount=request.total_amount,
            payment_method="COD",
            status="PENDING",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
        )

    monkeypatch.setattr(order_endpoint.order_service, "create_order", fake_create_order)

    response = client.post(
        "/api/v1/orders",
        json={
            "store_id": "store123",
            "customer_name": "Alice",
            "phone_number": "0123456789",
            "address": "123 Street",
            "items": [{"item_id": "1", "name": "Coffee", "quantity": 2, "price": 30000}],
            "total_amount": 60000,
            "currency": "VND",
            "payment_method": "COD",
        },
    )

    assert response.status_code == 200
    assert response.json()["order_id"] == "COD_123"
    assert response.json()["status"] == "PENDING"


def test_create_order_endpoint_rejects_unsupported_payment_method():
    response = client.post(
        "/api/v1/orders",
        json={
            "store_id": "store123",
            "customer_name": "Alice",
            "phone_number": "0123456789",
            "address": "123 Street",
            "items": [{"item_id": "1", "name": "Coffee", "quantity": 2, "price": 30000}],
            "total_amount": 60000,
            "payment_method": "BANK",
        },
    )

    assert response.status_code == 422


def test_validate_delivery_returns_warning_in_buffer_zone(monkeypatch):
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
        return 10.8, 106.72

    async def fake_road_distance(lat1: float, lon1: float, lat2: float, lon2: float):
        return 6.5

    monkeypatch.setattr(order_endpoint.GeoService, "geocode", fake_geocode)
    monkeypatch.setattr(order_endpoint.GeoService, "get_road_distance", fake_road_distance)

    response = client.post(
        "/api/v1/orders/validate-delivery",
        json={"store_id": "store123", "customer_address": "Far Street"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "WARNING_EXTRA_COST"


def test_validate_delivery_rejects_address_outside_buffer(monkeypatch):
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
        return 10.9, 106.9

    async def fake_road_distance(lat1: float, lon1: float, lat2: float, lon2: float):
        return 8.1

    monkeypatch.setattr(order_endpoint.GeoService, "geocode", fake_geocode)
    monkeypatch.setattr(order_endpoint.GeoService, "get_road_distance", fake_road_distance)

    response = client.post(
        "/api/v1/orders/validate-delivery",
        json={"store_id": "store123", "customer_address": "Too Far Street"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_validate_delivery_allows_when_store_address_missing(monkeypatch):
    monkeypatch.setattr(order_endpoint.store_repo, "get_store", lambda store_id: {"id": store_id})

    response = client.post(
        "/api/v1/orders/validate-delivery",
        json={"store_id": "store123", "customer_address": "123 Street"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ALLOWED"


def test_validate_delivery_rejects_when_customer_address_cannot_be_geocoded(monkeypatch):
    monkeypatch.setattr(
        order_endpoint.store_repo,
        "get_store",
        lambda store_id: {"id": store_id, "location": {"lat": 10.7769, "lng": 106.7009}},
    )

    async def fake_geocode(address: str):
        return None

    monkeypatch.setattr(order_endpoint.GeoService, "geocode", fake_geocode)

    response = client.post(
        "/api/v1/orders/validate-delivery",
        json={"store_id": "store123", "customer_address": "Unknown"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_geocode_endpoint_returns_coordinates(monkeypatch):
    async def fake_geocode(address: str):
        return 10.7769, 106.7009

    monkeypatch.setattr(order_endpoint.GeoService, "geocode", fake_geocode)

    response = client.get("/api/v1/orders/geocode", params={"address": "123 Street"})

    assert response.status_code == 200
    assert response.json() == {"lat": 10.7769, "lng": 106.7009}


def test_geocode_endpoint_returns_400_when_address_not_found(monkeypatch):
    async def fake_geocode(address: str):
        return None

    monkeypatch.setattr(order_endpoint.GeoService, "geocode", fake_geocode)

    response = client.get("/api/v1/orders/geocode", params={"address": "Unknown"})

    assert response.status_code == 400


def test_get_orders_returns_list(monkeypatch):
    mock_orders = [
        {"order_id": "ORD1", "store_id": "store123", "customer_name": "John", "phone_number": "0123", "status": "PENDING", "total_amount": 50000.0, "created_at": "2024-01-01T00:00:00"},
        {"order_id": "ORD2", "store_id": "store123", "customer_name": "Jane", "phone_number": "0456", "status": "CONFIRMED", "total_amount": 75000.0, "created_at": "2024-01-02T00:00:00"}
    ]

    def fake_get_orders(store_id, status=None, page=1, page_size=20):
        return {"total": 2, "page": 1, "page_size": 20, "total_pages": 1, "orders": mock_orders}

    monkeypatch.setattr(order_endpoint.order_service, "get_orders", fake_get_orders)

    response = client.get("/api/v1/orders", params={"store_id": "store123"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert len(data["orders"]) == 2


def test_get_orders_with_status_filter(monkeypatch):
    mock_orders = [
        {"order_id": "ORD1", "store_id": "store123", "customer_name": "John", "phone_number": "0123", "status": "PENDING", "total_amount": 50000.0, "created_at": "2024-01-01T00:00:00"}
    ]

    def fake_get_orders(store_id, status=None, page=1, page_size=20):
        return {"total": 1, "page": 1, "page_size": 20, "total_pages": 1, "orders": mock_orders}

    monkeypatch.setattr(order_endpoint.order_service, "get_orders", fake_get_orders)

    response = client.get("/api/v1/orders", params={"store_id": "store123", "status": "PENDING"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["orders"][0]["status"] == "PENDING"


def test_get_order_detail_success(monkeypatch):
    mock_order = {
        "id": "ORD1",
        "store_id": "store123",
        "customer_name": "John Doe",
        "phone_number": "0123456789",
        "address": "123 Street",
        "order_info": "",
        "items": [{"item_id": "1", "name": "Coffee", "quantity": 2, "price": 30000}],
        "total_amount": 60000,
        "currency": "VND",
        "payment_method": "COD",
        "status": "PENDING",
        "created_at": "2024-01-01T00:00:00"
    }

    monkeypatch.setattr(order_endpoint.order_service.order_repo, "get_order", lambda x: mock_order)

    response = client.get("/api/v1/orders/ORD1")

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "ORD1"
    assert data["customer_name"] == "John Doe"
    assert data["status"] == "PENDING"


def test_get_order_detail_not_found(monkeypatch):
    monkeypatch.setattr(order_endpoint.order_service.order_repo, "get_order", lambda x: None)

    response = client.get("/api/v1/orders/ORD999")

    assert response.status_code == 404


def test_update_order_status_success(monkeypatch):
    monkeypatch.setattr(
        order_endpoint.order_service,
        "update_order_status",
        lambda order_id, status: {"success": True, "order_id": order_id, "status": status}
    )

    response = client.put(
        "/api/v1/orders/ORD1/status",
        json={"status": "CONFIRMED"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "CONFIRMED"


def test_update_order_status_not_found(monkeypatch):
    monkeypatch.setattr(
        order_endpoint.order_service,
        "update_order_status",
        lambda order_id, status: {"success": False, "error": "Order not found"}
    )

    response = client.put(
        "/api/v1/orders/ORD999/status",
        json={"status": "CONFIRMED"}
    )

    assert response.status_code == 404


def test_verify_payment_success(monkeypatch):
    monkeypatch.setattr(
        order_endpoint.order_service,
        "verify_payment",
        lambda order_id, amount_paid: {
            "matched": True,
            "order_id": order_id,
            "expected_amount": 100000,
            "paid_amount": amount_paid,
            "message": "Payment verified successfully"
        }
    )

    response = client.post(
        "/api/v1/orders/ORD1/verify-payment",
        json={"order_id": "ORD1", "amount_paid": 100000.0}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is True
    assert data["status"] == "PAID"


def test_verify_payment_mismatch(monkeypatch):
    monkeypatch.setattr(
        order_endpoint.order_service,
        "verify_payment",
        lambda order_id, amount_paid: {
            "matched": False,
            "order_id": order_id,
            "expected_amount": 100000,
            "paid_amount": amount_paid,
            "message": f"Amount mismatch: expected 100000, got {amount_paid}"
        }
    )

    response = client.post(
        "/api/v1/orders/ORD1/verify-payment",
        json={"order_id": "ORD1", "amount_paid": 90000.0}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False
    assert data["status"] == "PENDING"

