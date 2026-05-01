from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "payment"}

def test_root_not_found():
    response = client.get("/")
    assert response.status_code == 404
