from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class OrderItem(BaseModel):
    name: str
    quantity: int
    price: int

class PaymentCreateRequest(BaseModel):
    amount: int
    store_id: str
    order_info: Optional[str] = "Thanh toan don hang"
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    items: Optional[List[OrderItem]] = []

class PaymentCreateResponse(BaseModel):
    order_id: str
    qr_data: str # EMVCo string
    qr_image_url: str
    amount: int
    content: str
    expired_at: datetime

class PaymentStatusResponse(BaseModel):
    order_id: str
    status: str # PENDING, NOTIFIED, PAID, FAILED, EXPIRED
    amount: int
    address: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: Optional[datetime] = None
