import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.websocket_manager import WebSocketManager


client = TestClient(app)


@pytest.fixture
def manager():
    return WebSocketManager()


@pytest.mark.asyncio
async def test_connect_adds_connection(manager):
    mock_ws = AsyncMock()
    await manager.connect(mock_ws, "store123")

    assert "store123" in manager.active_connections
    assert mock_ws in manager.active_connections["store123"]
    assert manager.get_connection_count("store123") == 1


@pytest.mark.asyncio
async def test_connect_multiple_connections_same_store(manager):
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    await manager.connect(mock_ws1, "store123")
    await manager.connect(mock_ws2, "store123")

    assert len(manager.active_connections["store123"]) == 2
    assert manager.get_connection_count("store123") == 2


@pytest.mark.asyncio
async def test_disconnect_removes_connection(manager):
    mock_ws = AsyncMock()
    await manager.connect(mock_ws, "store123")
    assert manager.get_connection_count("store123") == 1

    manager.disconnect(mock_ws, "store123")

    assert "store123" not in manager.active_connections
    assert manager.get_connection_count("store123") == 0


@pytest.mark.asyncio
async def test_disconnect_removes_only_one_connection(manager):
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    await manager.connect(mock_ws1, "store123")
    await manager.connect(mock_ws2, "store123")

    manager.disconnect(mock_ws1, "store123")

    assert len(manager.active_connections["store123"]) == 1
    assert mock_ws2 in manager.active_connections["store123"]


def test_disconnect_nonexistent_store(manager):
    mock_ws = AsyncMock()
    manager.disconnect(mock_ws, "nonexistent")  # Should not raise
    assert manager.get_connection_count("nonexistent") == 0


@pytest.mark.asyncio
async def test_broadcast_to_store(manager):
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    await manager.connect(mock_ws1, "store123")
    await manager.connect(mock_ws2, "store123")

    message = {"type": "order:new", "order_id": "ORD1"}
    await manager.broadcast_to_store("store123", message)

    mock_ws1.send_json.assert_called_once_with(message)
    mock_ws2.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_to_nonexistent_store(manager):
    # Should not raise
    await manager.broadcast_to_store("nonexistent", {"type": "test"})


@pytest.mark.asyncio
async def test_broadcast_handles_errors(manager):
    mock_ws_good = AsyncMock()
    mock_ws_bad = AsyncMock()
    mock_ws_bad.send_json.side_effect = Exception("Connection closed")

    await manager.connect(mock_ws_good, "store123")
    await manager.connect(mock_ws_bad, "store123")

    message = {"type": "test"}
    await manager.broadcast_to_store("store123", message)

    # Bad connection should be disconnected
    assert mock_ws_bad not in manager.active_connections["store123"]
    # Good connection should still be there
    assert mock_ws_good in manager.active_connections["store123"]


@pytest.mark.asyncio
async def test_send_personal_message(manager):
    mock_ws = AsyncMock()
    message = {"type": "test", "data": "hello"}

    await manager.send_personal_message(message, mock_ws)

    mock_ws.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_send_personal_message_handles_error(manager):
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = Exception("Connection closed")

    # Should not raise
    await manager.send_personal_message({"type": "test"}, mock_ws)

