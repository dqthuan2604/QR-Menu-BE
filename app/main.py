from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.websocket_manager import manager as websocket_manager

from app.core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="QR-Menu Payment Service",
    description="Backend service cho thanh toán VietQR",
    version="1.0.0",
)

# Rate Limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware - cho phép tất cả origin (development/ngrok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/{store_id}")
async def websocket_endpoint(websocket: WebSocket, store_id: str):
    """
    WebSocket endpoint cho real-time notification.
    Client kết nối qua ws://host:port/ws/{store_id}
    """
    await websocket_manager.connect(websocket, store_id)
    try:
        while True:
            # Keep connection alive, nhận message nếu cần
            _data = await websocket.receive_text()
            # Có thể xử lý message từ client ở đây nếu cần
    except Exception as e:
        logger.error(f"WebSocket error for store {store_id}: {e}")
    finally:
        websocket_manager.disconnect(websocket, store_id)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "payment"}

app.include_router(api_router, prefix="/api/v1")
