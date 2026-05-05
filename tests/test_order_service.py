import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.order_service import OrderService
from app.schemas.order import OrderCreateRequest, OrderItemSchema

@pytest.fixture
def order_service():
    with patch('app.services.order_service.OrderRepository') as mock_repo, \
         patch('app.services.order_service.store_repo') as mock_store_repo, \
         patch('app.services.order_service.TelegramHelper') as mock_telegram:

        service = OrderService()
        service.order_repo = mock_repo.return_value
        service.store_repo = mock_store_repo
        service.telegram = mock_telegram.return_value
        yield service

def test_create_cod_order_success(order_service):
    items = [OrderItemSchema(item_id="1", name="Coffee", quantity=2, price=30000)]
    request = OrderCreateRequest(
        store_id="store123",
        customer_name="John Doe",
        phone_number="0123456789",
        address="123 Street",
        items=items,
        total_amount=60000,
        currency="VND",
        payment_method="COD"
    )

    order_service.order_repo.create_cod_order.return_value = {
        "id": "COD_12345",
        "store_id": "store123",
        "customer_name": "John Doe",
        "phone_number": "0123456789",
        "address": "123 Street",
        "order_info": "",
        "items": [{"name": "Coffee", "quantity": 2, "price": 30000}],
        "total_amount": 60000,
        "currency": "VND",
        "payment_method": "COD",
        "status": "PENDING",
        "created_at": "2024-04-27T00:00:00"
    }

    order_service.store_repo.get_store.return_value = {
        "id": "store123",
        "name": "My Store",
        "telegram_chat_id": 987654321
    }

    order_service.telegram.send_cod_notification.return_value = "msg_id_123"

    response = order_service.create_order(request)

    assert response.order_id == "COD_12345"
    assert response.status == "PENDING"
    order_service.order_repo.create_cod_order.assert_called_once()
    order_service.telegram.send_cod_notification.assert_called_once()
    order_service.order_repo.update_status.assert_called_with("COD_12345", "PENDING", {"telegram_message_id": "msg_id_123"})

def test_create_cod_order_without_telegram_config_does_not_send_notification(order_service):
    items = [OrderItemSchema(item_id="1", name="Coffee", quantity=1, price=30000)]
    request = OrderCreateRequest(
        store_id="store123",
        customer_name="John Doe",
        phone_number="0123456789",
        address="123 Street",
        items=items,
        total_amount=30000,
        currency="VND",
        payment_method="COD"
    )
    order_service.order_repo.create_cod_order.return_value = {
        "id": "COD_12345",
        "store_id": "store123",
        "customer_name": "John Doe",
        "phone_number": "0123456789",
        "address": "123 Street",
        "order_info": "",
        "items": [{"name": "Coffee", "quantity": 1, "price": 30000}],
        "total_amount": 30000,
        "currency": "VND",
        "payment_method": "COD",
        "status": "PENDING",
        "created_at": "2024-04-27T00:00:00"
    }
    order_service.store_repo.get_store.return_value = {"id": "store123", "name": "My Store"}

    response = order_service.create_order(request)

    assert response.order_id == "COD_12345"
    order_service.telegram.send_cod_notification.assert_not_called()
    order_service.order_repo.update_status.assert_not_called()

def test_get_orders_with_filters(order_service):
    mock_orders = [
        {"id": "ORD1", "store_id": "store123", "status": "PENDING", "total_amount": 50000},
        {"id": "ORD2", "store_id": "store123", "status": "PENDING", "total_amount": 75000}
    ]
    order_service.order_repo.get_orders_by_store.return_value = (mock_orders, 2)

    result = order_service.get_orders(store_id="store123", status="PENDING", page=1, page_size=10)

    assert result["total"] == 2
    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["total_pages"] == 1
    assert len(result["orders"]) == 2
    order_service.order_repo.get_orders_by_store.assert_called_once_with(
        store_id="store123", status="PENDING", limit=10, offset=0
    )

def test_get_orders_empty_result(order_service):
    order_service.order_repo.get_orders_by_store.return_value = ([], 0)

    result = order_service.get_orders(store_id="store123")

    assert result["total"] == 0
    assert result["total_pages"] == 0
    assert result["orders"] == []

def test_update_order_status_success(order_service, monkeypatch):
    order_service.order_repo.get_order.return_value = {
        "id": "ORD1",
        "store_id": "store123",
        "status": "PENDING"
    }

    import asyncio
    mock_create_task = MagicMock()
    monkeypatch.setattr(asyncio, "create_task", mock_create_task)

    result = order_service.update_order_status(order_id="ORD1", status="CONFIRMED")

    assert result["success"] is True
    assert result["status"] == "CONFIRMED"
    order_service.order_repo.update_status.assert_called_once_with("ORD1", "CONFIRMED")
    mock_create_task.assert_called_once()

def test_update_order_status_order_not_found(order_service):
    order_service.order_repo.get_order.return_value = None

    result = order_service.update_order_status(order_id="ORD999", status="CONFIRMED")

    assert result["success"] is False
    assert "error" in result
    order_service.order_repo.update_status.assert_not_called()

def test_verify_payment_match(order_service):
    order_service.order_repo.get_order.return_value = {
        "id": "ORD1",
        "store_id": "store123",
        "total_amount": 100000,
        "status": "PENDING"
    }

    result = order_service.verify_payment(order_id="ORD1", amount_paid=100000.0)

    assert result["matched"] is True
    assert result["order_id"] == "ORD1"
    assert "successfully" in result["message"]
    order_service.order_repo.update_status.assert_called_once_with("ORD1", "PAID")

def test_verify_payment_mismatch(order_service):
    order_service.order_repo.get_order.return_value = {
        "id": "ORD1",
        "store_id": "store123",
        "total_amount": 100000,
        "status": "PENDING"
    }

    result = order_service.verify_payment(order_id="ORD1", amount_paid=90000.0)

    assert result["matched"] is False
    assert result["order_id"] == "ORD1"
    assert "mismatch" in result["message"]
    order_service.order_repo.update_status.assert_not_called()

def test_verify_payment_order_not_found(order_service):
    order_service.order_repo.get_order.return_value = None

    result = order_service.verify_payment(order_id="ORD999", amount_paid=100000.0)

    assert result["matched"] is False
    assert "error" in result
    order_service.order_repo.update_status.assert_not_called()
