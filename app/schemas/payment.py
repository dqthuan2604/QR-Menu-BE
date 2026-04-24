from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Order & Payment Schemas ---

class OrderItem(BaseModel):
    name: str
    quantity: int
    price: float

class PaymentCreateRequest(BaseModel):
    amount: float
    store_id: str
    order_info: Optional[str] = "Thanh toan don hang"
    customer_name: Optional[str] = "Khach vang lai"
    phone_number: Optional[str] = None
    address: Optional[str] = None
    items: Optional[List[OrderItem]] = []

class PaymentCreateResponse(BaseModel):
    order_id: str
    qr_data: str
    qr_image_url: str
    amount: float
    content: str
    expired_at: datetime

class PaymentStatusResponse(BaseModel):
    order_id: str
    status: str
    amount: float
    address: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: Optional[datetime] = None

# --- Store & Configuration Schemas ---

class StoreConfigRequest(BaseModel):
    name: str = Field(..., example="Loco Cafe")
    bank_code: Optional[str] = Field(None, example="VCB")
    bank_account: Optional[str] = Field(None, example="123456789")
    bank_account_name: Optional[str] = Field(None, example="NGUYEN VAN A")
    telegram_bot_username: Optional[str] = Field(None, example="QR_Menu_Bot")

class StoreResponse(BaseModel):
    store_id: str
    name: str
    bank_code: Optional[str] = None
    bank_bin: Optional[str] = None
    bank_account: Optional[str] = None
    bank_account_name: Optional[str] = None
    telegram_bot_username: Optional[str] = None
    telegram_chat_id: Optional[int] = None
    is_active: bool = True
