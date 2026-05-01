from datetime import datetime
import os
from app.core.config import settings
from app.utils.vietqr_helper import generate_vietqr_image_url, generate_vietqr_text
from app.repositories.order_repo import OrderRepository
from app.repositories.store_repo import store_repo
from app.core.bank_constants import get_bank_bin
from typing import Optional
from app.schemas.payment import PaymentCreateResponse, PaymentStatusResponse, PaymentCreateRequest
from app.utils.telegram_helper import TelegramHelper

class PaymentService:
    def __init__(self):
        self.order_repo = OrderRepository()
        self.store_repo = store_repo
        self.telegram = TelegramHelper()

    def create_payment(self, request: PaymentCreateRequest) -> PaymentCreateResponse:
        """
        Khởi tạo luồng thanh toán với cấu hình động từ Store Database
        """
        # 1. Lấy cấu hình cửa hàng từ Firestore
        store_config = self.store_repo.get_store(request.store_id)
        
        # Nếu không có cấu hình trong DB, dùng mặc định từ .env (phục vụ quá trình chuyển đổi)
        bank_bin = settings.bank_bin
        bank_account = settings.bank_account
        bank_account_name = settings.bank_account_name
        
        if store_config:
            # Ưu tiên lấy từ DB của Store
            db_bank_code = store_config.get("bank_code")
            bank_bin = store_config.get("bank_bin", bank_bin)
            bank_account = store_config.get("bank_account", bank_account)
            bank_account_name = store_config.get("bank_account_name", bank_account_name)
            
            # Nếu vẫn thiếu thông tin ngân hàng, thử lấy từ profile của chủ quán
            if not db_bank_code or not bank_account:
                owner_id = store_config.get("ownerId") # Firestore field is ownerId
                if owner_id:
                    owner_bank = self.store_repo.get_owner_bank_config(owner_id)
                    if owner_bank:
                        db_bank_code = owner_bank.get("bank_code", db_bank_code)
                        bank_account = owner_bank.get("bank_account", bank_account)
                        bank_account_name = owner_bank.get("bank_account_name", bank_account_name)

            if db_bank_code:
                mapped_bin = get_bank_bin(db_bank_code)
                if mapped_bin:
                    bank_bin = mapped_bin

        # 2. Tạo đơn hàng
        items_data = [item.dict() for item in request.items] if request.items else []
        order = self.order_repo.create_order(
            amount=request.amount, 
            store_id=request.store_id, 
            order_info=request.order_info,
            address=request.address,
            phone_number=request.phone_number,
            customer_name=request.customer_name,
            items=items_data,
            currency=request.currency
        )
        
        transfer_content = f"CK {order['id']}"
        
        # 3. Tạo QR dựa trên thông tin thực của cửa hàng
        qr_amount = int(request.amount)
        qr_image_url = generate_vietqr_image_url(
            bank_bin=bank_bin,
            account_no=bank_account,
            amount=qr_amount,
            content=transfer_content,
            account_name=bank_account_name
        )
        
        qr_data = generate_vietqr_text(
            bank_bin=bank_bin,
            account_no=bank_account,
            amount=qr_amount,
            content=transfer_content
        )
        
        # 3. Gửi thông báo "Đơn đang chờ thanh toán" cho Admin ngay lập tức
        store_config = self.store_repo.get_store(request.store_id)
        if store_config and store_config.get("telegram_chat_id"):
            chat_id = store_config["telegram_chat_id"]
            # Tạo message với trạng thái "ĐANG CHỜ"
            wait_message = self.telegram.format_bank_transfer_message(order)
            wait_message = wait_message.replace("🔔 <b>💰 KHÁCH BÁO CHUYỂN KHOẢN</b>", "⏳ <b>ĐƠN ĐANG CHỜ THANH TOÁN</b>")
            # Gửi tin nhắn thông báo kèm nút bấm và lưu ID
            msg_id = self.telegram.send_bank_notification(wait_message, order['id'], chat_id)
            if msg_id:
                self.order_repo.update_status(order['id'], "PENDING", {"telegram_message_id": msg_id})

        return PaymentCreateResponse(
            order_id=order['id'],
            qr_data=qr_data,
            qr_image_url=qr_image_url,
            amount=request.amount,
            content=transfer_content,
            expired_at=order['expired_at']
        )

    def notify_paid(self, order_id: str):
        """
        Gửi thông báo hoặc Cập nhật tin nhắn tới chủ quán khi khách báo đã chuyển tiền
        """
        order = self.order_repo.get_order(order_id)
        if not order:
            return False
            
        self.order_repo.update_status(order_id, "NOTIFIED", {"notified_at": datetime.now()})
        
        # Lấy Chat ID của cửa hàng từ DB
        store_config = self.store_repo.get_store(order['store_id'])
        chat_id = store_config.get("telegram_chat_id") if store_config else None
        
        if not chat_id:
            return False

        message = self.telegram.format_bank_transfer_message(order)
        msg_id = order.get("telegram_message_id")

        if msg_id:
            # Edit tin nhắn cũ thành "KHÁCH BÁO CHUYỂN KHOẢN" và hiện nút xác nhận
            self.telegram.edit_bank_notification(chat_id, msg_id, message, order_id)
        else:
            # Nếu chưa có msg_id thì gửi mới (fallback)
            self.telegram.send_bank_notification(message, order_id, chat_id=chat_id)
        
        return True

    def handle_telegram_start(self, chat_id: int, text: str):
        """
        Xử lý lệnh /start {store_id} để tự động liên kết Bot
        """
        if text.startswith("/start "):
            param = text.replace("/start ", "").strip()
            if param:
                # 1. Thử tìm theo ID trước
                store = self.store_repo.get_store(param)
                
                # 2. Nếu không thấy ID, thử tìm theo Bot Username (name nhập từ FE)
                if not store:
                    store = self.store_repo.find_by_bot_username(param)
                
                if store:
                    store_id = store['id']
                    self.store_repo.update_telegram_chat_id(store_id, chat_id)
                    self.telegram.send_message(
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
                    self.telegram.send_message(f"❌ Không tìm thấy cửa hàng với mã hoặc tên: <code>{param}</code>", chat_id)
            else:
                # Phản hồi khi nhấn /start mà không có tham số
                self.telegram.send_message(
                    "👋 <b>Chào mừng bạn đến với QR Menu Bot!</b>\n\n"
                    "Để liên kết Bot với cửa hàng của bạn, vui lòng sử dụng mã QR trong Dashboard hoặc nhấn vào link liên kết từ trang quản trị.\n\n"
                    "🚀 Bot này sẽ giúp bạn nhận thông báo đơn hàng mới tức thì!", 
                    chat_id
                )
        elif text == "/start":
             # Phản hồi cho lệnh /start thuần túy
             self.telegram.send_message(
                "👋 <b>Chào mừng bạn đến với QR Menu Bot!</b>\n\n"
                "Tôi đã sẵn sàng! Hãy quét mã QR từ Dashboard để bắt đầu nhận thông báo nhé.", 
                chat_id
            )

    def confirm_paid(self, order_id: str, secret: str):
        expected_secret = os.getenv("ADMIN_CONFIRM_SECRET", "admin123")
        if secret != expected_secret:
            return False, "Unauthorized"
            
        order = self.order_repo.get_order(order_id)
        if not order:
            return False, "Order not found"
            
        if order['status'] == "PAID":
            return True, "Order already paid"
            
        self.order_repo.update_status(order_id, "PAID", {"confirmed_at": datetime.now()})
        return True, "Success"

    def cancel_order(self, order_id: str, reason: str = "Customer cancelled"):
        """
        Hủy đơn hàng và cập nhật tin nhắn Telegram nếu có
        """
        order = self.order_repo.get_order(order_id)
        if not order:
            return False
            
        self.order_repo.update_status(order_id, "CANCELLED", {"cancelled_at": datetime.now(), "cancel_reason": reason})
        
        # Cập nhật Telegram
        store_config = self.store_repo.get_store(order['store_id'])
        chat_id = store_config.get("telegram_chat_id") if store_config else None
        msg_id = order.get("telegram_message_id")
        
        if chat_id and msg_id:
            message = self.telegram.format_bank_transfer_message(order)
            new_text = f"{message}\n\n❌ <b>TRẠNG THÁI: {reason.upper()}</b>"
            self.telegram.edit_message_text(chat_id, msg_id, new_text)
            
        return True

    def get_payment_status(self, order_id: str) -> Optional[PaymentStatusResponse]:
        order = self.order_repo.get_order(order_id)
        if not order:
            return None
            
        # Kiểm tra tự động hủy nếu hết hạn (Auto-expiration)
        current_status = order['status']
        if current_status in ["PENDING", "NOTIFIED"]:
            expired_at = order.get("expired_at")
            if expired_at:
                # Firestore returns datetime objects
                if datetime.now() > expired_at:
                    self.cancel_order(order_id, "Hết hạn thanh toán (Auto-expired)")
                    current_status = "CANCELLED"

        return PaymentStatusResponse(
            order_id=order['id'],
            status=current_status,
            amount=order['amount'],
            address=order.get('address'),
            phone_number=order.get('phone_number'),
            created_at=order.get('created_at')
        )
