from fastapi import APIRouter, HTTPException
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.services.order_service import OrderService

router = APIRouter()
order_service = OrderService()

@router.post("", response_model=OrderResponse)
async def create_order(request: OrderCreateRequest):
    """
    Tạo đơn hàng mới (Chỉ hỗ trợ COD).
    """
    try:
        return order_service.create_order(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
