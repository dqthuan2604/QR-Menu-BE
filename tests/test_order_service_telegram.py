from unittest.mock import patch

import pytest

from app.services.order_service import OrderService


@pytest.fixture
def order_service():
    with patch("app.services.order_service.OrderRepository") as mock_repo, \
         patch("app.services.order_service.store_repo") as mock_store_repo, \
         patch("app.services.order_service.TelegramHelper") as mock_telegram:
        service = OrderService()
        service.order_repo = mock_repo.return_value
        service.store_repo = mock_store_repo
        service.telegram = mock_telegram.return_value
        yield service


def test_handle_start_message_links_store_by_id(order_service):
    order_service.store_repo.get_store.return_value = {"id": "store123", "name": "Loco Cafe"}

    order_service.handle_telegram_update(
        {
            "message": {
                "chat": {"id": 987},
                "text": "/start store123",
            }
        }
    )

    order_service.store_repo.update_telegram_chat_id.assert_called_once_with("store123", 987)
    order_service.telegram.send_message.assert_called_once()


def test_handle_start_message_falls_back_to_bot_username(order_service):
    order_service.store_repo.get_store.return_value = None
    order_service.store_repo.find_by_bot_username.return_value = {
        "id": "store123",
        "name": "Loco Cafe",
    }

    order_service.handle_telegram_update(
        {
            "message": {
                "chat": {"id": 987},
                "text": "/start QR_Menu_Bot",
            }
        }
    )

    order_service.store_repo.find_by_bot_username.assert_called_once_with("QR_Menu_Bot")
    order_service.store_repo.update_telegram_chat_id.assert_called_once_with("store123", 987)


def test_handle_callback_query_confirms_cod_order(order_service):
    order_service.order_repo.get_order.return_value = {"id": "COD_123", "status": "PENDING"}

    order_service.handle_telegram_update(
        {
            "callback_query": {
                "id": "callback123",
                "data": "confirm_order:COD_123",
                "message": {
                    "chat": {"id": 987},
                    "message_id": 456,
                    "text": "Order details",
                },
            }
        }
    )

    order_service.order_repo.update_status.assert_called_once_with("COD_123", "CONFIRMED")
    order_service.telegram.edit_message_text.assert_called_once()
    order_service.telegram.answer_callback_query.assert_called_once_with(
        "callback123",
        "✅ Đã xác nhận đơn hàng!",
    )


def test_handle_callback_query_answers_when_order_missing(order_service):
    order_service.order_repo.get_order.return_value = None

    order_service.handle_telegram_update(
        {
            "callback_query": {
                "id": "callback123",
                "data": "confirm_order:missing",
                "message": {
                    "chat": {"id": 987},
                    "message_id": 456,
                    "text": "Order details",
                },
            }
        }
    )

    order_service.order_repo.update_status.assert_not_called()
    order_service.telegram.answer_callback_query.assert_called_once_with(
        "callback123",
        "❌ Không tìm thấy đơn hàng!",
    )


def test_handle_callback_query_ignores_malformed_data(order_service):
    order_service.handle_telegram_update(
        {
            "callback_query": {
                "id": "callback123",
                "data": "bad-data",
                "message": {"chat": {"id": 987}, "message_id": 456},
            }
        }
    )

    order_service.order_repo.get_order.assert_not_called()
    order_service.order_repo.update_status.assert_not_called()
