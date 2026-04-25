from datetime import datetime, timedelta
import uuid
from app.core.firebase import get_db

class OrderRepository:
    """
    Lớp quản lý tương tác trực tiếp với Google Firestore (Database).
    Tách biệt logic truy vấn khỏi logic nghiệp vụ của Service.
    """
    def __init__(self):
        # Lấy kết nối Database từ Firebase Admin SDK
        self.db = get_db()
        # Tên Collection trong Firestore
        self.collection = "orders" if self.db else None

    def create_order(self, amount: int, store_id: str, order_info: str, address: str = None, phone_number: str = None, customer_name: str = None, items: list = None, payment_method: str = "BANK", currency: str = "VND"):
        """
        Tạo mới một tài liệu (document) đơn hàng trong Firestore.
        """
        order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"
        order_data = {
            "id": order_id,
            "amount": amount,
            "currency": currency,
            "status": "PENDING",
            "store_id": store_id,
            "order_info": order_info,
            "address": address,
            "phone_number": phone_number,
            "customer_name": customer_name,
            "items": items or [],
            "payment_method": payment_method,
            "created_at": datetime.now(),
            "expired_at": datetime.now() + timedelta(minutes=15),
            "telegram_message_id": None
        }

        if not self.db:
            # Fallback nếu Firebase chưa được cấu hình (Dùng cho môi trường dev nhanh)
            print(f"⚠️ DEBUG: Creating MOCK order {order_id} (No Firebase)")
            return order_data

        # Ghi dữ liệu vào Firestore
        self.db.collection(self.collection).document(order_id).set(order_data)
        return order_data

    def create_cod_order(self, store_id: str, customer_name: str, phone_number: str, address: str, order_info: str, items: list, total_amount: float, currency: str = "VND"):
        """
        Tạo mới một đơn hàng Cash On Delivery (COD).
        """
        order_id = f"COD_{uuid.uuid4().hex[:8].upper()}"
        order_data = {
            "id": order_id,
            "store_id": store_id,
            "customer_name": customer_name,
            "phone_number": phone_number,
            "address": address,
            "order_info": order_info,
            "items": items,
            "total_amount": total_amount,
            "currency": currency,
            "payment_method": "COD",
            "status": "PENDING",
            "created_at": datetime.now(),
            "telegram_message_id": None
        }
        
        if self.db:
            self.db.collection(self.collection).document(order_id).set(order_data)
        return order_data

    def get_order(self, order_id: str):
        """
        Lấy thông tin chi tiết của một đơn hàng dựa trên ID.
        Trả về None nếu không tìm thấy.
        """
        if not self.db:
            return None
        doc = self.db.collection(self.collection).document(order_id).get()
        return doc.to_dict() if doc.exists else None

    def update_status(self, order_id: str, status: str, updated_fields: dict = None):
        """
        Cập nhật trạng thái và các trường dữ liệu bổ sung của đơn hàng.
        - status: PENDING, NOTIFIED, PAID.
        - updated_fields: Các thông tin timestamp (notified_at, confirmed_at).
        """
        if not self.db:
            print(f"⚠️ DEBUG: Updating MOCK order {order_id} to status {status}")
            return False
        
        data = {"status": status}
        if updated_fields:
            data.update(updated_fields)
            
        # Sử dụng update() để chỉ ghi đè các trường chỉ định, giữ nguyên các trường cũ
        self.db.collection(self.collection).document(order_id).update(data)
        return True
