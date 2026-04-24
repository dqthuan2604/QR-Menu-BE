from app.repositories.order_repo import OrderRepository
from app.repositories.store_repo import store_repo
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.utils.telegram_helper import TelegramHelper

class OrderService:
    def __init__(self):
        self.order_repo = OrderRepository()
        self.store_repo = store_repo
        self.telegram = TelegramHelper()

    def create_order(self, request: OrderCreateRequest) -> OrderResponse:
        # 1. Lưu order vào Firestore
        items_dict = [item.dict() for item in request.items]
        
        order_data = self.order_repo.create_cod_order(
            store_id=request.store_id,
            customer_name=request.customer_name,
            phone_number=request.phone_number,
            address=request.address,
            order_info=request.order_info or "",
            items=items_dict,
            total_amount=request.total_amount
        )
        
        # 2. Lấy thông tin cửa hàng để lấy telegram_chat_id
        store_config = self.store_repo.get_store(request.store_id)
        
        # 3. Bắn thông báo Telegram (nếu có cấu hình)
        if store_config and store_config.get("telegram_chat_id"):
            chat_id = store_config["telegram_chat_id"]
            
            # Format danh sách món ăn
            items_text = ""
            for item in request.items:
                note_str = f" <i>(Ghi chú: {item.note})</i>" if item.note else ""
                items_text += f"▪️ <b>{item.name}</b>{note_str}\n   └─ {item.quantity} x {item.price:,.0f}đ = <b>{item.price * item.quantity:,.0f}đ</b>\n"
                
            telegram_msg = (
                f"🛍 <b>ĐƠN HÀNG MỚI #{order_data['id'][:8].upper()}</b>\n"
                f"───────────────────\n"
                f"👤 <b>Khách:</b> {request.customer_name}\n"
                f"📞 <b>SĐT:</b> <code>{request.phone_number}</code>\n"
                f"📍 <b>Địa chỉ:</b> {request.address}\n"
                f"📝 <b>Ghi chú:</b> {request.order_info or 'Không có'}\n"
                f"───────────────────\n"
                f"<b>📋 DANH SÁCH MÓN:</b>\n"
                f"{items_text}\n"
                f"💰 <b>TỔNG CỘNG: {request.total_amount:,.0f}đ</b>\n"
                f"───────────────────\n"
                f"<i>Vui lòng xử lý đơn hàng sớm!</i>"
            )
            
            # Gọi API Telegram gửi tin nhắn tương tác
            self.telegram.send_order_notification(telegram_msg, order_data['id'], chat_id)
            
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
    def handle_telegram_callback(self, callback_data: dict):
        """
        Xử lý sự kiện khi người dùng nhấn nút trên Telegram.
        """
        query = callback_data.get("callback_query")
        if not query:
            return
        
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
            self.telegram.answer_callback_query(callback_id, "❌ Không tìm thấy đơn hàng!")
            return

        # 2. Xử lý các hành động
        if action == "confirm_order":
            self.order_repo.update_status(order_id, "CONFIRMED")
            self.telegram.edit_order_to_confirmed(chat_id, message_id, original_text, order_id)
            self.telegram.answer_callback_query(callback_id, "✅ Đã xác nhận đơn hàng!")
            
        elif action == "cancel_order":
            self.order_repo.update_status(order_id, "CANCELLED")
            self.telegram.edit_order_to_final_state(chat_id, message_id, original_text, "❌ <b>ĐƠN HÀNG ĐÃ BỊ HỦY</b>")
            self.telegram.answer_callback_query(callback_id, "🚫 Đã hủy đơn hàng!")
            
        elif action == "complete_order":
            self.order_repo.update_status(order_id, "COMPLETED")
            self.telegram.edit_order_to_final_state(chat_id, message_id, original_text, "✅ <b>ĐƠN HÀNG ĐÃ HOÀN THÀNH</b>")
            self.telegram.answer_callback_query(callback_id, "🎉 Chúc mừng bạn đã hoàn thành đơn!")
