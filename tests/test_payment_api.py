from datetime import datetime

from fastapi.testclient import TestClient

from app.api.v1.endpoints import payment as payment_endpoint
from app.main import app
from app.schemas.payment import PaymentCreateResponse, PaymentStatusResponse


client = TestClient(app)


def test_create_payment_endpoint_returns_qr_payload(monkeypatch):
    def fake_create_payment(request):
        assert request.store_id == "store123"
        assert request.amount == 100000
        return PaymentCreateResponse(
            order_id="BANK_123",
            qr_data="vietqr://payment",
            qr_image_url="https://qr.image/123",
            amount=request.amount,
            content="CK BANK_123",
            expired_at=datetime(2026, 1, 1, 12, 0, 0),
        )

    monkeypatch.setattr(payment_endpoint.payment_service, "create_payment", fake_create_payment)

    response = client.post(
        "/api/v1/payment/create",
        json={
            "store_id": "store123",
            "amount": 100000,
            "order_info": "Lunch",
            "items": [{"name": "Coffee", "quantity": 2, "price": 50000}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == "BANK_123"
    assert body["qr_image_url"] == "https://qr.image/123"
    assert body["content"] == "CK BANK_123"


def test_create_payment_endpoint_rejects_missing_required_fields():
    response = client.post("/api/v1/payment/create", json={"amount": 100000})

    assert response.status_code == 422


def test_get_payment_status_endpoint_returns_404_when_order_missing(monkeypatch):
    monkeypatch.setattr(payment_endpoint.payment_service, "get_payment_status", lambda order_id: None)

    response = client.get("/api/v1/payment/status", params={"order_id": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_get_payment_status_endpoint_returns_status(monkeypatch):
    monkeypatch.setattr(
        payment_endpoint.payment_service,
        "get_payment_status",
        lambda order_id: PaymentStatusResponse(
            order_id=order_id,
            status="PAID",
            amount=100000,
            address="123 Street",
            phone_number="0123456789",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
        ),
    )

    response = client.get("/api/v1/payment/status", params={"order_id": "BANK_123"})

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"
    assert response.json()["amount"] == 100000


def test_notify_paid_endpoint_returns_success_when_notification_sent(monkeypatch):
    monkeypatch.setattr(payment_endpoint.payment_service, "notify_paid", lambda order_id: True)

    response = client.post("/api/v1/payment/notify-paid", params={"order_id": "BANK_123"})

    assert response.status_code == 200
    assert response.json() == {"message": "Notification sent to admin"}


def test_notify_paid_endpoint_returns_404_when_order_missing(monkeypatch):
    monkeypatch.setattr(payment_endpoint.payment_service, "notify_paid", lambda order_id: False)

    response = client.post("/api/v1/payment/notify-paid", params={"order_id": "missing"})

    assert response.status_code == 404


def test_cancel_order_endpoint_returns_success(monkeypatch):
    monkeypatch.setattr(payment_endpoint.payment_service, "cancel_order", lambda order_id, reason: True)

    response = client.post("/api/v1/payment/cancel", params={"order_id": "BANK_123"})

    assert response.status_code == 200
    assert response.json() == {"message": "Order cancelled"}


def test_confirm_paid_endpoint_returns_html_when_secret_valid(monkeypatch):
    monkeypatch.setattr(
        payment_endpoint.payment_service,
        "confirm_paid",
        lambda order_id, secret: (True, "Success"),
    )

    response = client.get(
        "/api/v1/payment/confirm-paid",
        params={"order_id": "BANK_123", "secret": "admin123"},
    )

    assert response.status_code == 200
    assert "Đã xác nhận đơn BANK_123 thành công" in response.text


def test_confirm_paid_endpoint_returns_400_when_secret_invalid(monkeypatch):
    monkeypatch.setattr(
        payment_endpoint.payment_service,
        "confirm_paid",
        lambda order_id, secret: (False, "Unauthorized"),
    )

    response = client.get(
        "/api/v1/payment/confirm-paid",
        params={"order_id": "BANK_123", "secret": "wrong"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unauthorized"


def test_get_store_config_endpoint_returns_store(monkeypatch):
    monkeypatch.setattr(
        payment_endpoint.payment_service.store_repo,
        "get_store",
        lambda store_id: {
            "name": "Loco Cafe",
            "bank_code": "VCB",
            "bank_bin": "970436",
            "bank_account": "123456789",
            "bank_account_name": "OWNER",
            "telegram_bot_username": "QR_Menu_Bot",
            "telegram_chat_id": 123,
            "is_active": True,
        },
    )

    response = client.get("/api/v1/payment/store/store123")

    assert response.status_code == 200
    assert response.json()["store_id"] == "store123"
    assert response.json()["bank_bin"] == "970436"


def test_get_store_config_endpoint_returns_404_when_store_missing(monkeypatch):
    monkeypatch.setattr(payment_endpoint.payment_service.store_repo, "get_store", lambda store_id: None)

    response = client.get("/api/v1/payment/store/missing")

    assert response.status_code == 404

