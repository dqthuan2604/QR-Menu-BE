import asyncio
import json
import logging
from typing import Any, Optional
from app.core.config import settings

class TelegramHelper:
    """
    Công cụ hỗ trợ giao tiếp với Telegram Bot API (async).
    Hỗ trợ gửi tin nhắn tương tác với Nút bấm (Inline Buttons).
    """
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.default_chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        logging.info(f"DEBUG: TelegramHelper initialized with token: {str(self.token)[:10]}... (len: {len(str(self.token))})")

    async def _post(self, endpoint: str, data: dict) -> dict:
        """Gửi POST request async qua httpx."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self.base_url}/{endpoint}", data=data)
                if resp.status_code == 200:
                    return resp.json()
                logging.error(f"DEBUG: Telegram {endpoint} failed: {resp.text}")
                return {}
        except Exception as e:
            logging.error(f"DEBUG: Telegram {endpoint} error: {e}")
            return {}

    async def send_message(self, text: str, chat_id: int) -> Optional[int]:
        """Gửi tin nhắn văn bản thông thường. Trả về message_id nếu thành công."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        data = await self._post("sendMessage", payload)
        return data.get("result", {}).get("message_id")

    async def send_cod_notification(self, text: str, order_id: str, chat_id: int) -> Optional[int]:
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
            "reply_markup": json.dumps(keyboard)
        }
        data = await self._post("sendMessage", payload)
        return data.get("result", {}).get("message_id")

    async def send_bank_notification(self, text: str, order_id: str, chat_id: int) -> Optional[int]:
        """Gửi thông báo đơn hàng BANK kèm nút Xác nhận đã nhận tiền"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Xác nhận thanh toán", "callback_data": f"confirm_paid:{order_id}"},
                    {"text": "❌ Hủy đơn hàng", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }
        data = await self._post("sendMessage", payload)
        return data.get("result", {}).get("message_id")

    async def send_interactive_message(self, text: str, order_id: str, chat_id: int) -> Optional[int]:
        """Mặc định coi là Bank notification nếu gọi hàm chung này"""
        return await self.send_bank_notification(text, order_id, chat_id)

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup: Optional[dict[str, Any]] = None) -> bool:
        """Cập nhật nội dung tin nhắn Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup is not None:
            if isinstance(reply_markup, dict):
                payload["reply_markup"] = json.dumps(reply_markup)
            else:
                payload["reply_markup"] = reply_markup
        else:
            payload["reply_markup"] = json.dumps({"inline_keyboard": []})

        data = await self._post("editMessageText", payload)
        return data.get("ok", False) if data else False

    async def edit_bank_notification(self, chat_id: int, message_id: int, text: str, order_id: str) -> bool:
        """Cập nhật tin nhắn BANK và hiển thị nút Xác nhận đã nhận tiền"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Xác nhận thanh toán", "callback_data": f"confirm_paid:{order_id}"},
                    {"text": "❌ Hủy đơn hàng", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]
        }
        return await self.edit_message_text(chat_id, message_id, text, reply_markup=keyboard)

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> None:
        payload = {
            "callback_query_id": callback_query_id,
            "text": text
        }
        await self._post("answerCallbackQuery", payload)

    def format_currency(self, amount: float, currency_code: str = "VND"):
        """Định dạng tiền tệ theo mã (VND, USD, EUR)"""
        if currency_code == "VND":
            return f"{amount:,.0f}".replace(",", ".") + "đ"
        elif currency_code == "USD":
            return f"${amount:,.2f}"
        elif currency_code == "EUR":
            formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{formatted} €"
        else:
            return f"{amount:,.2f} {currency_code}"

    def format_cod_message(self, order_data: dict):
        """Định dạng tin nhắn cho đơn hàng thanh toán khi nhận hàng (COD)"""
        currency = order_data.get("currency", "VND")
        items_str = ""
        for item in order_data.get("items", []):
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
