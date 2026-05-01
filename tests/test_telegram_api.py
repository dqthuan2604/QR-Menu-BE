from fastapi.testclient import TestClient

from app.api.v1.endpoints import telegram as telegram_endpoint
from app.main import app


client = TestClient(app)


def test_telegram_webhook_accepts_message_update(monkeypatch):
    calls = []

    def fake_handle(update):
        calls.append(update)

    monkeypatch.setattr(telegram_endpoint.order_service, "handle_telegram_update", fake_handle)

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "from": {"id": 987},
                "chat": {"id": 987},
                "text": "/start store123",
            }
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert calls[0]["message"]["text"] == "/start store123"


def test_telegram_webhook_accepts_invalid_json_without_failing():
    response = client.post(
        "/api/v1/telegram/webhook",
        content="not-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

