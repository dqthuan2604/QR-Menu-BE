import logging
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
        logging.info(f"DEBUG: TelegramHelper initialized with token: {str(self.token)[:10]}... (len: {len(str(self.token))})")

    def send_message(self, text: str, chat_id: int):
        """Gửi tin nhắn văn bản thông thường. Trả về message_id nếu thành công."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(f"{self.base_url}/sendMessage", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", {}).get("message_id")
            return None
        except Exception as e:
            logging.error(f"DEBUG: Telegram sendMessage error: {e}")
            return None

    def send_cod_notification(self, text: str, order_id: str, chat_id: int):
        """Gửi thông báo đơn hàng COD kèm nút Xác nhận đơn hàng"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Xác nhận đơn", "callback_data": f"confirm_order:{order_id}"},
                    {"text": "❌ Hủy đơn", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }
        try:
            resp = requests.post(f"{self.base_url}/sendMessage", json=payload)
            if resp.status_code == 200:
                return resp.json().get("result", {}).get("message_id")
            return None
        except:
            return None

    def send_bank_notification(self, text: str, order_id: str, chat_id: int):
        """Gửi thông báo đơn hàng BANK kèm nút Xác nhận đã nhận tiền"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "💰 Đã nhận tiền", "callback_data": f"confirm_paid:{order_id}"},
                    {"text": "❌ Hủy đơn", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }
        try:
            resp = requests.post(f"{self.base_url}/sendMessage", json=payload)
            if resp.status_code == 200:
                return resp.json().get("result", {}).get("message_id")
            return None
        except:
            return None

    def send_interactive_message(self, text: str, order_id: str, chat_id: int):
        """Mặc định coi là Bank notification nếu gọi hàm chung này"""
        return self.send_bank_notification(text, order_id, chat_id)

    def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup: dict = None):
        """Cập nhật nội dung tin nhắn Telegram."""
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        else:
            # Nếu muốn xóa bàn phím cũ, gửi inline_keyboard rỗng
            payload["reply_markup"] = {"inline_keyboard": []}

        try:
            resp = requests.post(f"{self.base_url}/editMessageText", json=payload)
            if resp.status_code != 200:
                logging.error(f"DEBUG: Telegram editMessageText failed: {resp.text}")
            return resp.status_code == 200
        except Exception as e:
            logging.error(f"DEBUG: Telegram editMessageText error: {e}")
            return False

    def edit_bank_notification(self, chat_id: int, message_id: int, text: str, order_id: str):
        """Cập nhật tin nhắn BANK và hiển thị nút Xác nhận đã nhận tiền"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "💰 Đã nhận tiền", "callback_data": f"confirm_paid:{order_id}"},
                    {"text": "❌ Hủy đơn", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]
        }
        return self.edit_message_text(chat_id, message_id, text, reply_markup=keyboard)

    def answer_callback_query(self, callback_query_id: str, text: str = None):
        payload = {
            "callback_query_id": callback_query_id,
            "text": text
        }
        try:
            requests.post(f"{self.base_url}/answerCallbackQuery", json=payload)
        except:
            pass

    def format_currency(self, amount: float, currency_code: str = "VND"):
        """Định dạng tiền tệ theo mã (VND, USD, EUR)"""
        if currency_code == "VND":
            # 2.000đ
            return f"{amount:,.0f}".replace(",", ".") + "đ"
        elif currency_code == "USD":
            # $2,000.00
            return f"${amount:,.2f}"
        elif currency_code == "EUR":
            # 2.000,00 €
            formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{formatted} €"
        else:
            return f"{amount:,.2f} {currency_code}"

    def format_cod_message(self, order_data: dict):
        """Định dạng tin nhắn cho đơn hàng thanh toán khi nhận hàng (COD)"""
        currency = order_data.get("currency", "VND")
        items_str = ""
        for item in order_data.get("items", []):
            price_formatted = self.format_currency(item['price'], currency)
            total_item_price = self.format_currency(item['price'] * item['quantity'], currency)
            items_str += f"• {item['name']} x {item['quantity']}: {total_item_price}\n"
        
        customer_name = order_data.get('customer_name', 'Khách vãng lai')
        phone = order_data.get('phone_number', 'N/A')
        address = order_data.get('address', 'N/A')
        total_amount = order_data.get('total_amount', order_data.get('amount', 0))
        total_formatted = self.format_currency(total_amount, currency)
        
        message = (
            f"🔔 <b>🚚 ĐƠN HÀNG COD MỚI</b>\n\n"
            f"👤 <b>Khách:</b> {customer_name}\n"
            f"📞 <b>SĐT:</b> <code>{phone}</code>\n"
            f"📍 <b>Địa chỉ:</b> {address}\n"
            f"---------------------------\n"
            f"💳 <b>Thanh toán:</b> Tiền mặt (COD)\n"
            f"---------------------------\n"
            f"📝 <b>Chi tiết món:</b>\n"
            f"{items_str or '• Không có thông tin món'}\n"
            f"---------------------------\n"
            f"💰 <b>TỔNG CỘNG: {total_formatted}</b>\n"
            f"---------------------------\n"
            f"<i>Vui lòng chuẩn bị món và liên hệ khách để giao hàng.</i>"
        )
        return message

    def format_bank_transfer_message(self, order_data: dict):
        """Định dạng tin nhắn cho đơn hàng chuyển khoản (VietQR)"""
        currency = order_data.get("currency", "VND")
        items_str = ""
        for item in order_data.get("items", []):
            price_formatted = self.format_currency(item['price'], currency)
            total_item_price = self.format_currency(item['price'] * item['quantity'], currency)
            items_str += f"• {item['name']} x {item['quantity']}: {total_item_price}\n"
        
        customer_name = order_data.get('customer_name', 'Khách vãng lai')
        phone = order_data.get('phone_number', 'N/A')
        address = order_data.get('address', 'N/A')
        total_amount = order_data.get('amount', order_data.get('total_amount', 0))
        total_formatted = self.format_currency(total_amount, currency)
        
        message = (
            f"🔔 <b>💰 KHÁCH BÁO CHUYỂN KHOẢN</b>\n\n"
            f"👤 <b>Khách:</b> {customer_name}\n"
            f"📞 <b>SĐT:</b> <code>{phone}</code>\n"
            f"📍 <b>Địa chỉ:</b> {address}\n"
            f"---------------------------\n"
            f"💳 <b>Thanh toán:</b> Chuyển khoản (VietQR)\n"
            f"---------------------------\n"
            f"📝 <b>Chi tiết món:</b>\n"
            f"{items_str or '• Không có thông tin món'}\n"
            f"---------------------------\n"
            f"💰 <b>TỔNG CỘNG: {total_formatted}</b>\n"
            f"📝 Nội dung CK: <code>CK {order_data.get('id', 'N/A')}</code>\n"
            f"---------------------------\n"
            f"⚠️ <b>LƯU Ý QUAN TRỌNG:</b>\n"
            f"<i>Vui lòng kiểm tra tài khoản ngân hàng của bạn để xác nhận tiền đã về trước khi nhấn nút 'Xác nhận'.</i>"
        )
        return message
