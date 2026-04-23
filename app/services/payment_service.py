from datetime import datetime
import os
from app.core.config import settings
from app.utils.vietqr_helper import generate_vietqr_image_url, generate_vietqr_text
from app.repositories.order_repo import OrderRepository
from app.schemas.payment import PaymentCreateResponse, PaymentStatusResponse, PaymentCreateRequest
from app.utils.telegram_helper import TelegramHelper

class PaymentService:
    """
    Lớp điều hướng toàn bộ quy trình nghiệp vụ thanh toán.
    Kết nối giữa API Router, Database (Repository) và các công cụ bên ngoài (VietQR, Telegram).
    """
    def __init__(self):
        self.order_repo = OrderRepository()
        self.telegram = TelegramHelper()

    def create_payment(self, request: PaymentCreateRequest) -> PaymentCreateResponse:
        """
        Khởi tạo luồng thanh toán:
        1. Chuyển đổi dữ liệu từ Request sang dạng Dict để lưu vào Firestore.
        2. Tạo bản ghi đơn hàng với trạng thái PENDING.
        3. Tạo chuỗi ký tự VietQR và URL hình ảnh QR tương ứng.
        """
        # Trích xuất dữ liệu món ăn
        items_data = [item.dict() for item in request.items] if request.items else []
        
        # Lưu vào database thông qua Repository
        order = self.order_repo.create_order(
            amount=request.amount, 
            store_id=request.store_id, 
            order_info=request.order_info,
            address=request.address,
            phone_number=request.phone_number,
            customer_name=request.customer_name,
            items=items_data
        )
        
        # Nội dung chuyển khoản theo cú pháp: CK [Mã đơn]
        # Ví dụ: CK ORD_ABC123
        transfer_content = f"CK {order['id']}"
        
        # Tạo URL hình ảnh QR (Sử dụng API của VietQR.io)
        qr_image_url = generate_vietqr_image_url(
            bank_bin=settings.bank_bin,
            account_no=settings.bank_account,
            amount=request.amount,
            content=transfer_content,
            account_name=settings.bank_account_name
        )
        
        # Tạo chuỗi QR text (Dùng để Frontend tự generate QR nếu không muốn dùng ảnh URL)
        qr_data = generate_vietqr_text(
            bank_bin=settings.bank_bin,
            account_no=settings.bank_account,
            amount=request.amount,
            content=transfer_content
        )
        
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
        Xử lý khi khách báo đã chuyển tiền:
        1. Kiểm tra đơn hàng có tồn tại không.
        2. Cập nhật trạng thái 'Khách đã báo' (NOTIFIED).
        3. Gửi tin nhắn Telegram kèm Link xác nhận cho chủ quán.
        """
        order = self.order_repo.get_order(order_id)
        if not order:
            return False
            
        # Ghi nhận thời điểm khách báo đã chuyển
        self.order_repo.update_status(order_id, "NOTIFIED", {"notified_at": datetime.now()})
        
        # Gửi Telegram tương tác (Kèm nút bấm Xác nhận/Hủy ngay trong chat)
        message = self.telegram.format_order_message(order)
        self.telegram.send_interactive_message(message, order_id)
        
        return True

    def confirm_paid(self, order_id: str, secret: str):
        """
        Xử lý khi chủ quán xác nhận đơn hàng:
        1. Kiểm tra mã bí mật (Secret) để tránh người lạ tự ý xác nhận.
        2. Kiểm tra trạng thái hiện tại (Tránh xác nhận trùng lặp).
        3. Cập nhật trạng thái đơn hàng sang PAID.
        """
        expected_secret = os.getenv("ADMIN_CONFIRM_SECRET", "default_secret")
        if secret != expected_secret:
            return False, "Unauthorized"
            
        order = self.order_repo.get_order(order_id)
        if not order:
            return False, "Order not found"
            
        # Nếu đã thanh toán rồi thì không cần làm gì thêm
        if order['status'] == "PAID":
            return True, "Order already paid"
            
        # Cập nhật trạng thái cuối cùng thành công
        self.order_repo.update_status(order_id, "PAID", {"confirmed_at": datetime.now()})
        return True, "Success"

    def get_payment_status(self, order_id: str) -> PaymentStatusResponse:
        """
        Truy vấn trạng thái đơn hàng để phản hồi cho Frontend.
        Dùng cho cơ chế Polling ở Client.
        """
        order = self.order_repo.get_order(order_id)
        if not order:
            return None
            
        return PaymentStatusResponse(
            order_id=order['id'],
            status=order['status'],
            amount=order['amount'],
            address=order.get('address'),
            phone_number=order.get('phone_number'),
            created_at=order.get('created_at')
        )
