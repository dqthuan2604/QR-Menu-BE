import logging
from fastapi import APIRouter, Request, BackgroundTasks
from app.services.order_service import OrderService

router = APIRouter()
order_service = OrderService()

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint nhận webhook từ Telegram khi người dùng tương tác với Bot.
    """
    try:
        data = await request.json()
        logging.info(f"DEBUG: Received Telegram webhook data: {data}")
        # Xử lý trong background để tránh timeout Telegram
        background_tasks.add_task(order_service.handle_telegram_update, data)
    except Exception as e:
        logging.error(f"DEBUG: Error parsing webhook JSON: {str(e)}")

    return {"status": "ok"}
