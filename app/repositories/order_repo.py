from datetime import datetime, timedelta
import uuid
from typing import Any, Optional
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

    def create_order(self, amount: float, store_id: str, order_info: str, address: Optional[str] = None, phone_number: Optional[str] = None, customer_name: Optional[str] = None, items: Optional[list[Any]] = None, payment_method: str = "BANK", currency: str = "VND"):
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
        if not doc.exists:
            return None
        data = doc.to_dict()
        if "id" in data:
            data["order_id"] = data.pop("id")
        else:
            data["order_id"] = doc.id
        if "amount" in data and "total_amount" not in data:
            data["total_amount"] = data.pop("amount")
        return data

    def update_status(self, order_id: str, status: str, updated_fields: Optional[dict[str, Any]] = None):
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

    def get_orders_by_store(
        self,
        store_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Lấy danh sách đơn hàng của cửa hàng với filter, search, sort và pagination.
        Returns: (orders, total_count)
        """
        if not self.db:
            return [], 0

        # Lấy tất cả đơn hàng của store (và filter status nếu có)
        query = self.db.collection(self.collection).where("store_id", "==", store_id)

        if status:
            query = query.where("status", "==", status)

        docs = query.stream()
        all_orders = []
        for doc in docs:
            data = doc.to_dict()
            # Map field `id` -> `order_id`
            if "id" in data:
                data["order_id"] = data.pop("id")
            else:
                data["order_id"] = doc.id
            # Map field `amount` -> `total_amount` (cho bank orders)
            if "amount" in data and "total_amount" not in data:
                data["total_amount"] = data.pop("amount")
            all_orders.append(data)

        # Filter theo search (order_id, customer_name, phone_number)
        if search:
            search_lower = search.lower()
            filtered_orders = []
            for order in all_orders:
                if (
                    search_lower in str(order.get("order_id", "")).lower()
                    or search_lower in str(order.get("customer_name", "")).lower()
                    or search_lower in str(order.get("phone_number", "")).lower()
                ):
                    filtered_orders.append(order)
            all_orders = filtered_orders

        # Filter theo date range
        if date_from:
            try:
                from datetime import datetime
                date_from_dt = datetime.fromisoformat(date_from)
                all_orders = [o for o in all_orders if o.get("created_at") and o["created_at"] >= date_from_dt]
            except (ValueError, TypeError):
                pass

        if date_to:
            try:
                from datetime import datetime, timedelta
                date_to_dt = datetime.fromisoformat(date_to) + timedelta(days=1)
                all_orders = [o for o in all_orders if o.get("created_at") and o["created_at"] < date_to_dt]
            except (ValueError, TypeError):
                pass

        # Sort
        reverse = (sort_order == "desc")
        if sort_by == "total_amount":
            all_orders.sort(key=lambda x: float(x.get("total_amount", 0) or 0), reverse=reverse)
        elif sort_by == "status":
            all_orders.sort(key=lambda x: str(x.get("status", "")), reverse=reverse)
        elif sort_by == "customer_name":
            all_orders.sort(key=lambda x: str(x.get("customer_name", "")).lower(), reverse=reverse)
        else:  # default: created_at
            all_orders.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=reverse)

        # Tổng số sau filter
        total_count = len(all_orders)

        # Pagination
        paginated = all_orders[offset:offset + limit]

        return paginated, total_count
