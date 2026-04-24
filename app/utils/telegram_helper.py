import requests
import os
import json
from app.core.config import settings

class TelegramHelper:
    """
    Công cụ hỗ trợ giao tiếp với Telegram Bot API.
    Hỗ trợ gửi tin nhắn tương tác với Nút bấm (Inline Buttons).
    """
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.default_chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        print(f"DEBUG: TelegramHelper initialized with token: {self.token[:10]}... (len: {len(self.token)})")

    def send_message(self, text: str, chat_id: int):
        """Gửi tin nhắn văn bản thông thường"""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        print(f"DEBUG: Sending message to {chat_id}: {text[:50]}...")
        try:
            resp = requests.post(f"{self.base_url}/sendMessage", json=payload)
            print(f"DEBUG: Telegram sendMessage response: {resp.status_code} - {resp.text}")
            return True
        except Exception as e:
            print(f"DEBUG: Telegram sendMessage error: {e}")
            return False

    def send_order_notification(self, text: str, order_id: str, chat_id: int):
        """Gửi thông báo đơn hàng mới kèm nút Xác nhận/Hủy"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Xác nhận", "callback_data": f"confirm_order:{order_id}"},
                    {"text": "❌ Hủy", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }
        try:
            requests.post(f"{self.base_url}/sendMessage", json=payload)
            return True
        except:
            return False

    def edit_order_to_confirmed(self, chat_id: int, message_id: int, text: str, order_id: str):
        """Cập nhật tin nhắn sang trạng thái đã xác nhận, hiển thị nút Hoàn thành/Hủy"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏁 Hoàn thành", "callback_data": f"complete_order:{order_id}"},
                    {"text": "❌ Hủy", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }
        try:
            requests.post(f"{self.base_url}/editMessageText", json=payload)
            return True
        except:
            return False

    def edit_order_to_final_state(self, chat_id: int, message_id: int, text: str, status_text: str):
        """Cập nhật tin nhắn sang trạng thái cuối cùng (Hủy/Hoàn thành), ẩn hết nút"""
        final_text = f"{text}\n\n───────────────────\n{status_text}"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": final_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps({"inline_keyboard": []})
        }
        try:
            requests.post(f"{self.base_url}/editMessageText", json=payload)
            return True
        except:
            return False

    def answer_callback_query(self, callback_query_id: str, text: str = None):
        payload = {
            "callback_query_id": callback_query_id,
            "text": text
        }
        try:
            requests.post(f"{self.base_url}/answerCallbackQuery", json=payload)
        except:
            pass

    def format_order_message(self, order_data: dict):
        items_str = ""
        for item in order_data.get("items", []):
            items_str += f"• {item['name']} x {item['quantity']}: {item['price']:,}đ\n"
        
        customer_name = order_data.get('customer_name', 'Khách vãng lai')
        phone = order_data.get('phone_number', 'N/A')
        address = order_data.get('address', 'N/A')
        
        message = (
            f"🔔 <b>CÓ ĐƠN HÀNG MỚI (DELIVERY)</b>\n\n"
            f"👤 <b>Khách:</b> {customer_name}\n"
            f"📞 <b>SĐT:</b> {phone}\n"
            f"📍 <b>Địa chỉ:</b> {address}\n"
            f"---------------------------\n"
            f"📝 <b>Chi tiết món:</b>\n"
            f"{items_str or '• Không có thông tin món'}\n"
            f"---------------------------\n"
            f"💰 <b>TỔNG CỘNG: {order_data['amount']:,} VND</b>\n"
            f"📝 ND chuyển khoản: <code>CK {order_data['id']}</code>\n"
            f"---------------------------\n"
            f"<i>Vui lòng kiểm tra tài khoản trước khi xác nhận.</i>"
        )
        return message
