from pydantic import BaseModel, field_validator
from typing import List, Optional, Literal, Union
from datetime import datetime

class OrderItemSchema(BaseModel):
    item_id: Optional[str] = None
    name: str
    price: float
    quantity: int
    note: Optional[str] = None
    image: Optional[str] = None

class OrderCreateRequest(BaseModel):
    store_id: str
    customer_name: str
    phone_number: str
    address: str
    order_info: Optional[str] = None
    items: List[OrderItemSchema]
    total_amount: float
    currency: Optional[str] = "VND"
    payment_method: Literal["COD"]

class OrderResponse(BaseModel):
    order_id: str
    store_id: str
    customer_name: str
    phone_number: str
    address: str
    order_info: Optional[str] = None
    items: List[OrderItemSchema]
    total_amount: float
    payment_method: str
    status: str
    created_at: datetime

class OrderStatusUpdateRequest(BaseModel):
    status: Literal["PENDING", "CONFIRMED", "PAID", "COMPLETED", "CANCELLED"]

class OrderDetailResponse(BaseModel):
    order_id: str
    store_id: str
    customer_name: str
    phone_number: str
    address: str
    order_info: Optional[str] = None
    items: List[OrderItemSchema]
    total_amount: float
    currency: str
    payment_method: str
    status: str
    created_at: datetime
    telegram_message_id: Optional[Union[str, int]] = None

    @field_validator('telegram_message_id', mode='before')
    @classmethod
    def validate_telegram_message_id(cls, v):
        if v is None:
            return None
        return str(v)

class OrderListItemResponse(BaseModel):
    order_id: str
    store_id: str
    customer_name: str
    phone_number: str
    total_amount: float
    status: str
    created_at: datetime

class OrderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    orders: List[OrderListItemResponse]

class PaymentReconciliationRequest(BaseModel):
    order_id: str
    amount_paid: float
    payment_reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentReconciliationResponse(BaseModel):
    order_id: str
    status: str
    matched: bool
    message: str

class DeliveryValidationRequest(BaseModel):
    store_id: str
    customer_address: str

class DeliveryValidationResponse(BaseModel):
    status: Literal["ALLOWED", "WARNING_EXTRA_COST", "REJECTED"]
    distance_km: Optional[float] = None
    message: str
