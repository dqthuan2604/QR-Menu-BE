import pytest
from unittest.mock import patch
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
    # Prepare request
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

    # Mock repository responses
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

    # Execute
    response = order_service.create_order(request)

    # Assert
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
