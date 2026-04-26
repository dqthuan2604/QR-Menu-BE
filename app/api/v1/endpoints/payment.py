from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.schemas.payment import (
    PaymentCreateRequest, 
    PaymentCreateResponse, 
    PaymentStatusResponse,
    StoreResponse,
    StoreConfigRequest
)
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

# --- Store Management Endpoints ---

@router.get("/store/{store_id}", response_model=StoreResponse)
def get_store_config(store_id: str):
    """
    Lấy thông tin cấu hình của cửa hàng.
    """
    config = payment_service.store_repo.get_store(store_id)
    if not config:
        raise HTTPException(status_code=404, detail="Store not found")
    
    return StoreResponse(store_id=store_id, **config)

@router.post("/store/{store_id}")
def update_store_config(store_id: str, config: StoreConfigRequest):
    """
    Cập nhật thông tin ngân hàng cho cửa hàng.
    """
    payment_service.store_repo.update_bank_config(store_id, config.dict())
    return {"status": "ok", "message": f"Updated config for {store_id}"}

@router.post("/test-notification/{store_id}")
async def test_notification(store_id: str):
    """
    Gửi tin nhắn thử nghiệm tới Telegram đã kết nối.
    """
    store = payment_service.store_repo.get_store(store_id)
    if not store or not store.get("telegram_chat_id"):
        raise HTTPException(status_code=400, detail="Store not connected to Telegram")
    
    payment_service.telegram.send_message(
        f"🔔 <b>THÔNG BÁO THỬ NGHIỆM</b>\n\n"
        f"Cửa hàng: <b>{store.get('name', store_id)}</b>\n"
        f"Trạng thái: Kết nối hoạt động tốt! ✅\n\n"
        f"Bạn sẽ nhận được thông báo tại đây khi có đơn hàng mới.",
        store["telegram_chat_id"]
    )
    return {"status": "ok"}


@router.api_route("/notify-paid", methods=["GET", "POST"])
async def notify_paid(order_id: str = Query(...)):
    """
    [KHÁCH HÀNG] Bước 3: Khách hàng xác nhận đã chuyển khoản xong.
    """
    success = payment_service.notify_paid(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Notification sent to admin"}

@router.post("/cancel")
async def cancel_order(order_id: str = Query(...)):
    """
    [KHÁCH HÀNG] Chủ động hủy đơn hàng.
    """
    success = payment_service.cancel_order(order_id, "Khách hàng chủ động hủy")
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order cancelled"}

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
    
    # 1. Xử lý tin nhắn văn bản (Ví dụ: /start {store_id})
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        print(f"📩 Telegram Message from {chat_id}: {text}")
        
        if text.startswith("/start"):
            payment_service.handle_telegram_start(chat_id, text)
            return {"status": "ok"}

    # 2. Xử lý nhấn nút (callback_query)
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        callback_data = callback["data"] 
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        original_text = callback["message"]["text"]
        
        # 1. Phản hồi ngay lập tức để dừng quay vòng loading trên Telegram
        payment_service.telegram.answer_callback_query(callback_id, "Đang xử lý...")
        
        # Tách Action và Order ID
        if ":" not in callback_data:
            return {"status": "ok"}
            
        action, order_id = callback_data.split(":")
        
        # Lấy thông tin khách hàng để log
        order = payment_service.order_repo.get_order(order_id)
        customer_name = order.get("customer_name", "N/A") if order else "N/A"
        address = order.get("address", "N/A") if order else "N/A"
        phone = order.get("phone_number", "N/A") if order else "N/A"
        
        print(f"🔘 Telegram Button: {action} | Order: {order_id} | Customer: {customer_name} | Phone: {phone} | Address: {address} | by ChatID: {chat_id}")
        
        if action == "confirm_paid":
            import os
            secret = os.getenv("ADMIN_CONFIRM_SECRET", "admin123")
            success, msg = payment_service.confirm_paid(order_id, secret)
            
            if success:
                # 2. Cập nhật text và GỠ BỎ NÚT BẤM (không cho bấm lần 2)
                new_text = f"{original_text}\n\n✅ <b>TRẠNG THÁI: ĐÃ XÁC NHẬN NHẬN TIỀN</b>"
                payment_service.telegram.edit_message_text(chat_id, message_id, new_text)
        
        elif action == "cancel_order":
            success = payment_service.cancel_order(order_id, "Đã hủy bởi Admin (Telegram)")
            if success:
                new_text = f"{original_text}\n\n❌ <b>TRẠNG THÁI: ĐÃ HỦY ĐƠN</b>"
                payment_service.telegram.edit_message_text(chat_id, message_id, new_text)

    return {"status": "ok"}
