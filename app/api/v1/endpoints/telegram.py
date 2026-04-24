from fastapi import APIRouter, Request, BackgroundTasks
from app.services.order_service import OrderService

router = APIRouter()
order_service = OrderService()

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint nhận webhook từ Telegram khi người dùng tương tác với Bot.
    """
    data = await request.json()
    
    # Xử lý trong background để tránh timeout Telegram
    background_tasks.add_task(order_service.handle_telegram_callback, data)
    
    return {"status": "ok"}
