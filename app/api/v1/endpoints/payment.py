from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.schemas.payment import PaymentCreateRequest, PaymentCreateResponse, PaymentStatusResponse
from app.services.payment_service import PaymentService
import logging

router = APIRouter()
payment_service = PaymentService()

@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(request: PaymentCreateRequest):
    """
    [KHÁCH HÀNG] Bước 1: Khởi tạo đơn hàng và lấy mã VietQR.
    """
    try:
        return payment_service.create_payment(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=PaymentStatusResponse)
async def get_payment_status(order_id: str):
    """
    [KHÁCH HÀNG/FRONTEND] Bước 2: Kiểm tra trạng thái đơn hàng (Polling).
    """
    status = payment_service.get_payment_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Order not found")
    return status

@router.post("/notify-paid")
async def notify_paid(order_id: str = Query(...)):
    """
    [KHÁCH HÀNG] Bước 3: Khách hàng xác nhận đã chuyển khoản xong.
    """
    success = payment_service.notify_paid(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Notification sent to admin"}

@router.get("/confirm-paid")
async def confirm_paid(order_id: str = Query(...), secret: str = Query(...)):
    """
    [CHỦ QUÁN] Xác nhận qua link (Dự phòng cho Phase 2).
    """
    success, message = payment_service.confirm_paid(order_id, secret)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=f"<h2>✅ Đã xác nhận đơn {order_id} thành công!</h2>")

@router.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    [HỆ THỐNG] Nhận tín hiệu từ Telegram khi anh nhấn Nút bấm (Inline Buttons).
    Đây là trung tâm xử lý cho Phase 3.
    """
    data = await request.json()
    print(f"📩 Incoming Telegram Webhook: {data}")
    
    # Kiểm tra xem có phải là sự kiện nhấn nút (callback_query) hay không
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        callback_data = callback["data"] 
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        original_text = callback["message"]["text"]
        
        print(f"🔘 Button Clicked: {callback_data} by ChatID: {chat_id}")
        
        # 1. Phản hồi ngay lập tức để dừng quay vòng loading trên Telegram
        payment_service.telegram.answer_callback_query(callback_id, "Đang xử lý...")
        
        # Tách Action và Order ID
        action, order_id = callback_data.split(":")
        
        if action == "confirm_paid":
            import os
            secret = os.getenv("ADMIN_CONFIRM_SECRET", "default_secret")
            success, msg = payment_service.confirm_paid(order_id, secret)
            
            if success:
                # 2. Cập nhật text và GỠ BỎ NÚT BẤM (không cho bấm lần 2)
                new_text = f"{original_text}\n\n✅ <b>TRẠNG THÁI: ĐÃ XÁC NHẬN NHẬN TIỀN</b>"
                payment_service.telegram.edit_message_text(chat_id, message_id, new_text)
        
        elif action == "cancel_order":
            new_text = f"{original_text}\n\n❌ <b>TRẠNG THÁI: ĐÃ HỦY ĐƠN</b>"
            payment_service.telegram.edit_message_text(chat_id, message_id, new_text)

    return {"status": "ok"}
