import asyncio
import logging
from datetime import datetime
from app.core.websocket_manager import manager
from typing import Optional
from app.repositories.order_repo import OrderRepository
from app.repositories.store_repo import store_repo
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.utils.telegram_helper import TelegramHelper

class OrderService:
    def __init__(self):
        self.order_repo = OrderRepository()
        self.store_repo = store_repo
        self.telegram = TelegramHelper()

    async def create_order(self, request: OrderCreateRequest) -> OrderResponse:
        # 1. Lưu order vào Firestore
        items_dict = [item.dict() for item in request.items]

        order_data = self.order_repo.create_cod_order(
            store_id=request.store_id,
            customer_name=request.customer_name,
            phone_number=request.phone_number,
            address=request.address,
            order_info=request.order_info or "",
            items=items_dict,
            total_amount=request.total_amount,
            currency=request.currency
        )

        # 2. Lấy thông tin cửa hàng để lấy telegram_chat_id
        store_config = self.store_repo.get_store(request.store_id)

        # 3. Bắn thông báo Telegram (nếu có cấu hình)
        if store_config and store_config.get("telegram_chat_id"):
            chat_id = store_config["telegram_chat_id"]

            # Sử dụng hàm định dạng chuyên biệt cho COD
            telegram_msg = self.telegram.format_cod_message(order_data)

            # Gọi API Telegram gửi tin nhắn tương tác cho đơn COD
            msg_id = await self.telegram.send_cod_notification(telegram_msg, order_data['id'], chat_id)
            if msg_id:
                self.order_repo.update_status(order_data['id'], "PENDING", {"telegram_message_id": msg_id})

        # Broadcast đơn hàng mới qua WebSocket
        store_id = request.store_id
        if store_id:
            asyncio.create_task(
                manager.broadcast_to_store(
                    store_id=store_id,
                    message={
                        "type": "order:new",
                        "order_id": order_data["id"],
                        "customer_name": order_data["customer_name"],
                        "total_amount": order_data["total_amount"],
                        "status": order_data["status"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            )

        return OrderResponse(
            order_id=order_data["id"],
            store_id=order_data["store_id"],
            customer_name=order_data["customer_name"],
            phone_number=order_data["phone_number"],
            address=order_data["address"],
            order_info=order_data["order_info"],
            items=request.items,
            total_amount=order_data["total_amount"],
            payment_method=order_data["payment_method"],
            status=order_data["status"],
            created_at=order_data["created_at"]
        )

    async def handle_telegram_update(self, callback_data: dict):
        """
        Hệ thống điều phối (Dispatcher) cho các cập nhật từ Telegram Webhook.
        Xử lý cả Callback Query (nút bấm) và Message (văn bản).
        """
        # 1. Xử lý Callback Query (Nút bấm)
        if "callback_query" in callback_data:
            logging.info("DEBUG: Detected callback_query")
            await self._handle_callback_query(callback_data["callback_query"])

        # 2. Xử lý Message (Lệnh văn bản như /start)
        elif "message" in callback_data:
            logging.info("DEBUG: Detected message")
            await self._handle_message(callback_data["message"])
        else:
            logging.info("DEBUG: No supported update type found in data")

    async def _handle_message(self, message: dict):
        """Xử lý các tin nhắn văn bản từ người dùng"""
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        logging.info(f"DEBUG: Handling message from {chat_id}: {text}")

        if not chat_id or not text:
            logging.info("DEBUG: Missing chat_id or text")
            return

        if text.startswith("/start"):
            logging.info("DEBUG: Start command detected")
            # Trích xuất tham số sau /start (ví dụ: /start store_123)
            parts = text.split(" ")
            param = parts[1] if len(parts) > 1 else ""
            logging.info(f"DEBUG: Start param: {param}")

            if param:
                # Tìm cửa hàng theo ID hoặc Bot Username
                store = self.store_repo.get_store(param)
                if not store:
                    store = self.store_repo.find_by_bot_username(param)

                if store:
                    store_id = store['id']
                    self.store_repo.update_telegram_chat_id(store_id, chat_id)
                    await self.telegram.send_message(
                        f"✅ <b>KẾT NỐI THÀNH CÔNG!</b>\n\n"
                        f"🏪 Cửa hàng: <b>{store.get('name', store_id)}</b>\n"
                        f"🔗 ID Hệ thống: <code>{store_id}</code>\n\n"
                        f"🎉 Từ bây giờ, tôi sẽ tự động gửi thông báo đến đây mỗi khi:\n"
                        f"• Có đơn hàng mới được tạo.\n"
                        f"• Khách hàng thanh toán thành công.\n\n"
                        f"<i>Bạn có thể quay lại Dashboard và nhấn nút 'Gửi thử' để kiểm tra lại đường truyền nhé!</i>",
                        chat_id
                    )
                else:
                    await self.telegram.send_message(f"❌ Không tìm thấy cửa hàng với mã hoặc tên: <code>{param}</code>", chat_id)
            else:
                await self.telegram.send_message(
                    "👋 <b>Chào mừng bạn đến với QR Menu Bot!</b>\n\n"
                    "Để liên kết Bot với cửa hàng, vui lòng sử dụng mã QR trong Dashboard hoặc nhấn vào link liên kết từ trang quản trị.",
                    chat_id
                )

    async def _handle_callback_query(self, query: dict):
        """Xử lý khi người dùng nhấn nút bấm và broadcast qua WebSocket"""
        callback_id = query["id"]
        data = query.get("data", "")
        message = query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        original_text = message.get("text", "")

        if not data or not chat_id or not message_id:
            return

        # Phân tích cú pháp data: "action:order_id"
        parts = data.split(":")
        if len(parts) < 2:
            return

        action = parts[0]
        order_id = parts[1]

        # 1. Lấy thông tin order từ DB
        order = self.order_repo.get_order(order_id)
        if not order:
            await self.telegram.answer_callback_query(callback_id, "❌ Không tìm thấy đơn hàng!")
            return

        new_status = None
        # 2. Xử lý các hành động
        if action == "confirm_order":
            new_status = "CONFIRMED"
            self.order_repo.update_status(order_id, new_status)
            new_text = f"{original_text}\n\n✅ <b>TRẠNG THÁI: ĐÃ XÁC NHẬN ĐƠN</b>"
            await self.telegram.edit_message_text(chat_id, message_id, new_text)
            await self.telegram.answer_callback_query(callback_id, "✅ Đã xác nhận đơn hàng!")

        elif action == "confirm_paid":
            new_status = "PAID"
            self.order_repo.update_status(order_id, new_status)
            new_text = f"{original_text}\n\n✅ <b>TRẠNG THÁI: ĐÃ NHẬN TIỀN</b>"
            await self.telegram.edit_message_text(chat_id, message_id, new_text)
            await self.telegram.answer_callback_query(callback_id, "💰 Đã xác nhận nhận tiền!")

        elif action == "cancel_order":
            new_status = "CANCELLED"
            self.order_repo.update_status(order_id, new_status)
            new_text = f"{original_text}\n\n❌ <b>TRẠNG THÁI: ĐÃ HỦY ĐƠN</b>"
            await self.telegram.edit_message_text(chat_id, message_id, new_text)
            await self.telegram.answer_callback_query(callback_id, "🚫 Đã hủy đơn hàng!")

        elif action == "complete_order":
            new_status = "COMPLETED"
            self.order_repo.update_status(order_id, new_status)
            new_text = f"{original_text}\n\n✅ <b>TRẠNG THÁI: ĐÃ HOÀN THÀNH</b>"
            await self.telegram.edit_message_text(chat_id, message_id, new_text)
            await self.telegram.answer_callback_query(callback_id, "🎉 Chúc mừng bạn đã hoàn thành đơn!")

        # 3. Broadcast sự kiện tới cửa hàng qua WebSocket
        if new_status and order:
            store_id = order.get("store_id")
            if store_id:
                asyncio.create_task(
                    manager.broadcast_to_store(
                        store_id=store_id,
                        message={
                            "type": "order:telegram_action",
                            "order_id": order_id,
                            "action": action,
                            "new_status": new_status,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                )

    def get_orders(
        self,
        store_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ):
        """
        Lấy danh sách đơn hàng của cửa hàng với filter, search, sort.
        """
        offset = (page - 1) * page_size
        orders, total_count = self.order_repo.get_orders_by_store(
            store_id=store_id,
            status=status,
            limit=page_size,
            offset=offset,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            date_from=date_from,
            date_to=date_to
        )

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "orders": orders
        }

    async def update_order_status(self, order_id: str, status: str) -> dict:
        """
        Cập nhật trạng thái đơn hàng, broadcast WebSocket và cập nhật Telegram (async).
        """
        order = self.order_repo.get_order(order_id)
        if not order:
            return {"success": False, "error": "Order not found"}

        self.order_repo.update_status(order_id, status)

        # Cập nhật tin nhắn Telegram nếu có (chạy trong thread riêng để không block)
        telegram_message_id = order.get("telegram_message_id")
        if telegram_message_id:
            store_id = order.get("store_id")
            if store_id:
                store_config = self.store_repo.get_store(store_id)
                if store_config and store_config.get("telegram_chat_id"):
                    chat_id = store_config["telegram_chat_id"]
                    new_text = self._format_status_message(order, status)
                    reply_markup = self._get_keyboard_for_status(order_id, status)

                    async def _update_telegram():
                        await asyncio.to_thread(
                            self.telegram.edit_message_text,
                            int(chat_id),
                            int(str(telegram_message_id)),
                            new_text,
                            reply_markup
                        )

                    asyncio.create_task(_update_telegram())

        # Broadcast sự kiện tới cửa hàng qua WebSocket
        store_id = order.get("store_id")
        if store_id:
            asyncio.create_task(
                manager.broadcast_to_store(
                    store_id=store_id,
                    message={
                        "type": "order:status_changed",
                        "order_id": order_id,
                        "new_status": status,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            )

        return {"success": True, "order_id": order_id, "status": status}

    def _format_status_message(self, order: dict, status: str) -> str:
        """Format tin nhắn cập nhật trạng thái cho Telegram."""
        status_labels = {
            "CONFIRMED": "✅ <b>TRẠNG THÁI: ĐÃ XÁC NHẬN ĐƠN</b>",
            "PAID": "✅ <b>TRẠNG THÁI: ĐÃ NHẬN TIỀN</b>",
            "COMPLETED": "✅ <b>TRẠNG THÁI: ĐÃ HOÀN THÀNH</b>",
            "CANCELLED": "❌ <b>TRẠNG THÁI: ĐÃ HỦY ĐƠN</b>"
        }
        status_text = status_labels.get(status, f"<b>TRẠNG THÁI: {status}</b>")

        customer_name = order.get('customer_name', 'Khách vãng lai')
        phone = order.get('phone_number', 'N/A')
        total_amount = order.get('total_amount', order.get('amount', 0))
        currency = order.get('currency', 'VND')
        total_formatted = self.telegram.format_currency(total_amount, currency)

        return (
            f"🔔 <b>ĐƠN HÀNG CẬP NHẬT</b>\n\n"
            f"👤 <b>Khách:</b> {customer_name}\n"
            f"📞 <b>SĐT:</b> <code>{phone}</code>\n"
            f"💰 <b>Tổng cộng:</b> {total_formatted}\n\n"
            f"{status_text}"
        )

    def _get_keyboard_for_status(self, order_id: str, status: str) -> dict:
        """Lấy inline keyboard dựa trên trạng thái mới."""
        if status == "PENDING":
            return {"inline_keyboard": [
                [
                    {"text": "✅ Xác nhận đơn", "callback_data": f"confirm_order:{order_id}"},
                    {"text": "❌ Hủy đơn", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]}
        elif status == "CONFIRMED":
            return {"inline_keyboard": [
                [
                    {"text": "✅ Xác nhận thanh toán", "callback_data": f"confirm_paid:{order_id}"},
                    {"text": "❌ Hủy đơn", "callback_data": f"cancel_order:{order_id}"}
                ]
            ]}
        elif status == "PAID":
            return {"inline_keyboard": [
                [
                    {"text": "✅ Hoàn thành", "callback_data": f"complete_order:{order_id}"}
                ]
            ]}
        else:
            # COMPLETED hoặc CANCELLED - không có nút bấm
            return {"inline_keyboard": []}

    def verify_payment(self, order_id: str, amount_paid: float) -> dict:
        """
        Đối soát thông tin thanh toán.
        """
        order = self.order_repo.get_order(order_id)
        if not order:
            return {"matched": False, "error": "Order not found"}

        expected_amount = order.get("total_amount", 0)
        matched = abs(float(amount_paid) - float(expected_amount)) < 0.01

        if matched:
            self.order_repo.update_status(order_id, "PAID")
            return {
                "matched": True,
                "order_id": order_id,
                "expected_amount": expected_amount,
                "paid_amount": amount_paid,
                "message": "Payment verified successfully"
            }
        else:
            return {
                "matched": False,
                "order_id": order_id,
                "expected_amount": expected_amount,
                "paid_amount": amount_paid,
                "message": f"Amount mismatch: expected {expected_amount}, got {amount_paid}"
            }
