from fastapi import APIRouter
from app.api.v1.endpoints import payment, order, telegram

api_router = APIRouter()
api_router.include_router(payment.router, prefix="/payment", tags=["Payment"])
api_router.include_router(order.router, prefix="/orders", tags=["Order"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])
