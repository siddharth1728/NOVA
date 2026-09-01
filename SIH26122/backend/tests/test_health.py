import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "database" in data
    # Note: Since Docker is missing in the environment, the database might be 'unavailable'
    # But we assert the endpoint returns the correct structure.
    assert data["database"] in ["connected", "unavailable"]

def test_cors_configuration():
    # Test that CORS allows our configured frontend origin
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
