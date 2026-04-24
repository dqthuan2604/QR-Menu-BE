from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class OrderItemSchema(BaseModel):
    item_id: str
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
