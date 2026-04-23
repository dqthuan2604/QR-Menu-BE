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
        self.chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_interactive_message(self, text: str, order_id: str):
        """
        Gửi tin nhắn kèm theo các nút bấm tương tác (Inline Keyboard).
        """
        if not self.token or not self.chat_id:
            return False
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Xác nhận đã nhận tiền",
                        "callback_data": f"confirm_paid:{order_id}"
                    },
                    {
                        "text": "❌ Hủy đơn",
                        "callback_data": f"cancel_order:{order_id}"
                    }
                ]
            ]
        }
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }
        
        try:
            requests.post(f"{self.base_url}/sendMessage", json=payload)
            return True
        except:
            return False

    def answer_callback_query(self, callback_query_id: str, text: str = None):
        """
        Phản hồi lại lệnh nhấn nút để dừng trạng thái loading trên Telegram.
        """
        payload = {
            "callback_query_id": callback_query_id,
            "text": text
        }
        try:
            requests.post(f"{self.base_url}/answerCallbackQuery", json=payload)
        except:
            pass

    def edit_message_text(self, chat_id: int, message_id: int, new_text: str):
        """
        Cập nhật lại nội dung tin nhắn và GỠ BỎ NÚT BẤM (để chống spam).
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps({"inline_keyboard": []}) # Gửi keyboard rỗng để xóa nút
        }
        try:
            requests.post(f"{self.base_url}/editMessageText", json=payload)
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
