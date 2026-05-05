from __future__ import annotations

import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, store_id: str) -> None:
        await websocket.accept()
        if store_id not in self.active_connections:
            self.active_connections[store_id] = []
        self.active_connections[store_id].append(websocket)
        logger.info(f"WebSocket connected for store_id={store_id}")

    def disconnect(self, websocket: WebSocket, store_id: str) -> None:
        if store_id in self.active_connections:
            if websocket in self.active_connections[store_id]:
                self.active_connections[store_id].remove(websocket)
                logger.info(f"WebSocket disconnected for store_id={store_id}")
            if not self.active_connections[store_id]:
                del self.active_connections[store_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_store(self, store_id: str, message: dict) -> None:
        if store_id not in self.active_connections:
            return
        disconnected: List[WebSocket] = []
        connections = list(self.active_connections[store_id])

        # Dùng asyncio.gather để gửi concurrent thay vì tuần tự
        async def _send(conn):
            try:
                await conn.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to store {store_id}: {e}")
                disconnected.append(conn)

        await asyncio.gather(*[_send(conn) for conn in connections], return_exceptions=True)

        for conn in disconnected:
            self.disconnect(conn, store_id)

    def get_connection_count(self, store_id: str) -> int:
        return len(self.active_connections.get(store_id, []))


# Singleton instance để sử dụng xuyên suốt ứng dụng
manager = WebSocketManager()
