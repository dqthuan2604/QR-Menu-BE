import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from app.services.payment_service import PaymentService
from app.schemas.payment import PaymentCreateRequest

@pytest.fixture
def payment_service():
    with patch('app.services.payment_service.OrderRepository') as mock_repo, \
         patch('app.services.payment_service.store_repo') as mock_store_repo, \
         patch('app.services.payment_service.TelegramHelper') as mock_telegram, \
         patch('app.services.payment_service.generate_vietqr_image_url') as mock_qr_img, \
         patch('app.services.payment_service.generate_vietqr_text') as mock_qr_text:
        
        service = PaymentService()
        service.order_repo = mock_repo.return_value
        service.store_repo = mock_store_repo
        service.telegram = mock_telegram.return_value
        service.mock_qr_img = mock_qr_img
        service.mock_qr_text = mock_qr_text
        yield service

def test_create_payment_success(payment_service):
    # Prepare request
    request = PaymentCreateRequest(
        store_id="store123",
        amount=100000,
        order_info="Coffee break",
        customer_name="Alice",
        phone_number="0987654321",
        items=[]
    )

    # Mock responses
    payment_service.store_repo.get_store.return_value = {
        "id": "store123",
        "bank_bin": "970415",
        "bank_account": "123456789",
        "bank_account_name": "STORE OWNER",
        "telegram_chat_id": 987654321
    }
    
    payment_service.order_repo.create_order.return_value = {
        "id": "BANK_123",
        "amount": 100000,
        "store_id": "store123",
        "expired_at": "2024-04-27T01:00:00"
    }
    
    payment_service.mock_qr_img.return_value = "https://qr.image/123"
    payment_service.mock_qr_text.return_value = "000201010212..."
    payment_service.telegram.send_bank_notification.return_value = "msg_id_456"

    # Execute
    response = payment_service.create_payment(request)

    # Assert
    assert response.order_id == "BANK_123"
    assert "https://qr.image/123" in response.qr_image_url
    payment_service.order_repo.create_order.assert_called_once()
    payment_service.telegram.send_bank_notification.assert_called_once()
    payment_service.order_repo.update_status.assert_called_with("BANK_123", "PENDING", {"telegram_message_id": "msg_id_456"})

def test_confirm_paid_success(payment_service):
    # Mock responses
    payment_service.order_repo.get_order.return_value = {
        "id": "BANK_123",
        "status": "PENDING"
    }
    
    with patch('os.getenv', return_value="admin123"):
        success, message = payment_service.confirm_paid("BANK_123", "admin123")
    
    assert success is True
    assert message == "Success"
    payment_service.order_repo.update_status.assert_called()

def test_confirm_paid_rejects_invalid_secret(payment_service):
    with patch('os.getenv', return_value="admin123"):
        success, message = payment_service.confirm_paid("BANK_123", "wrong-secret")

    assert success is False
    assert message == "Unauthorized"
    payment_service.order_repo.get_order.assert_not_called()
    payment_service.order_repo.update_status.assert_not_called()

def test_get_payment_status_returns_none_when_order_missing(payment_service):
    payment_service.order_repo.get_order.return_value = None

    assert payment_service.get_payment_status("missing") is None

def test_get_payment_status_auto_cancels_expired_pending_order(payment_service):
    payment_service.order_repo.get_order.return_value = {
        "id": "BANK_123",
        "status": "PENDING",
        "amount": 100000,
        "expired_at": datetime.now() - timedelta(minutes=1),
        "address": "123 Street",
        "phone_number": "0123456789",
        "created_at": datetime.now(),
        "store_id": "store123",
    }
    payment_service.store_repo.get_store.return_value = None

    response = payment_service.get_payment_status("BANK_123")

    assert response is not None
    assert response.status == "CANCELLED"
    payment_service.order_repo.update_status.assert_called_with(
        "BANK_123",
        "CANCELLED",
        {
            "cancelled_at": payment_service.order_repo.update_status.call_args.args[2]["cancelled_at"],
            "cancel_reason": "Hết hạn thanh toán (Auto-expired)",
        },
    )

def test_create_payment_uses_owner_bank_config_when_store_bank_missing(payment_service):
    request = PaymentCreateRequest(
        store_id="store123",
        amount=125000.75,
        order_info="Dinner",
        items=[],
    )
    payment_service.store_repo.get_store.return_value = {
        "id": "store123",
        "ownerId": "owner123",
        "bank_account": None,
    }
    payment_service.store_repo.get_owner_bank_config.return_value = {
        "bank_code": "VCB",
        "bank_account": "987654321",
        "bank_account_name": "OWNER NAME",
    }
    payment_service.order_repo.create_order.return_value = {
        "id": "BANK_123",
        "amount": 125000.75,
        "store_id": "store123",
        "expired_at": datetime.now(),
    }
    payment_service.mock_qr_img.return_value = "https://qr.image/owner"
    payment_service.mock_qr_text.return_value = "vietqr://owner"

    response = payment_service.create_payment(request)

    assert response.order_id == "BANK_123"
    payment_service.mock_qr_img.assert_called_once()
    qr_kwargs = payment_service.mock_qr_img.call_args.kwargs
    assert qr_kwargs["bank_bin"] == "970436"
    assert qr_kwargs["account_no"] == "987654321"
    assert qr_kwargs["amount"] == 125000
