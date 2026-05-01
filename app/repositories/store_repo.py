from app.core.firebase import get_db
from google.cloud.firestore import Client
from typing import Optional, Dict, Any, cast

class StoreRepository:
    def __init__(self):
        self.db: Client = get_db()
        self.collection = "restaurants"

    def get_store(self, store_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin cấu hình của cửa hàng theo ID"""
        doc = cast(Any, self.db.collection(self.collection).document(store_id).get())
        if doc.exists:
            data = doc.to_dict() or {}
            data['id'] = doc.id
            return data
        return None

    def find_by_bot_username(self, bot_username: str) -> Optional[Dict[str, Any]]:
        """Tìm cửa hàng theo tên định danh Bot đã cấu hình"""
        docs = self.db.collection(self.collection).where("telegram_bot_username", "==", bot_username).limit(1).get()
        for doc in docs:
            data = doc.to_dict() or {}
            data['id'] = doc.id
            return data
        return None

    def update_telegram_chat_id(self, store_id: str, chat_id: int):
        """Cập nhật Chat ID khi chủ quán nhấn Start trên Telegram"""
        self.db.collection(self.collection).document(store_id).update({
            "telegram_chat_id": chat_id
        })

    def update_bank_config(self, store_id: str, bank_config: Dict[str, Any]):
        """Cập nhật cấu hình ngân hàng (dùng cho trang Admin)"""
        self.db.collection(self.collection).document(store_id).set(bank_config, merge=True)

    def get_owner_bank_config(self, owner_id: str) -> Optional[Dict[str, Any]]:
        """Lấy cấu hình ngân hàng từ profile của chủ quán"""
        doc = cast(Any, self.db.collection("users").document(owner_id).get())
        if doc.exists:
            data = doc.to_dict() or {}
            return data.get("bank_config")
        return None

store_repo = StoreRepository()
