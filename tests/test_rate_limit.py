import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock

# Create a clean TestClient
client = TestClient(app)

def test_rate_limit_geocode():
    """
    Test rate limiting on geocode endpoint (Limit: 60/minute)
    We will try to call it 61 times.
    """
    # Mock GeoService.geocode to avoid external API calls
    with patch("app.services.geo_service.GeoService.geocode") as mock_geocode:
        mock_geocode.return_value = (10.762622, 106.660172)
        
        # Call 60 times - should be successful
        for i in range(60):
            response = client.get("/api/v1/orders/geocode?address=Ho%20Chi%20Minh")
            if response.status_code != 200:
                pytest.fail(f"Failed at call {i+1}: {response.status_code} {response.text}")
            
        # The 61st call should return 429
        response = client.get("/api/v1/orders/geocode?address=Ho%20Chi%20Minh")
        if response.status_code != 429:
            pytest.fail(f"Expected 429 but got {response.status_code}. Content: {response.text}")
        
        # Check if it has 'detail' or 'error' or something else
        content = response.json()
        assert ("detail" in content or "error" in content)
        print(f"Geocode Rate Limit Content: {content}")

def test_rate_limit_orders():
    """
    Test rate limiting on order creation (Limit: 25/minute)
    """
    order_data = {
        "store_id": "test_store",
        "customer_name": "Test User",
        "phone_number": "0901234567",
        "address": "123 Test St",
        "order_info": "Extra spicy",
        "items": [
            {"item_id": "p1", "name": "Banh Mi", "price": 20000, "quantity": 1}
        ],
        "total_amount": 20000,
        "currency": "VND",
        "payment_method": "COD"
    }
    
    # Mock order_service.create_order to avoid Firebase writes
    with patch("app.services.order_service.OrderService.create_order") as mock_create:
        # Create a mock response that matches OrderResponse schema
        mock_create.return_value = {
            "order_id": "COD_TEST",
            "store_id": "test_store",
            "customer_name": "Test User",
            "phone_number": "0901234567",
            "address": "123 Test St",
            "order_info": "Extra spicy",
            "items": [{"item_id": "p1", "name": "Banh Mi", "price": 20000, "quantity": 1}],
            "total_amount": 20000,
            "payment_method": "COD",
            "status": "PENDING",
            "created_at": "2024-01-01T00:00:00"
        }
        
        # Call 25 times
        for i in range(25):
            response = client.post("/api/v1/orders", json=order_data)
            if response.status_code != 200:
                pytest.fail(f"Failed at call {i+1}: {response.status_code} {response.text}")
        
        # The 26th call should return 429
        response = client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 429

